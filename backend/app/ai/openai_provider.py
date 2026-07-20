"""Concrete OpenAI implementation of the AIProvider Protocol.

Each public method:
  1. Builds a structured prompt requesting a JSON response.
  2. Calls the OpenAI chat completions API using the async client.
  3. Parses and validates the JSON response with Pydantic.
  4. Wraps errors in the appropriate domain exception.
  5. Is decorated with tenacity retry logic (3 attempts, exponential backoff)
     for transient failures (timeout / unavailability).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any
from urllib.parse import quote_plus

import httpx
import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.ai.exceptions import AIResponseError, AITimeoutError, AIUnavailableError
from app.ai.provider import (
    AnswerFeedback,
    GapCategory,
    InterviewQuestion,
    LearningResource,
    ProficiencyLevel,
    ProjectSuggestion,
    RoadmapTopic,
    Skill,
    SkillGap,
    SkillRequirement,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Roadmap resource-curation tuning ──────────────────────────────────────────
_MIN_RESOURCES = 2          # RoadmapTopic requires at least this many
_TARGET_RESOURCES = 3       # aim for this many live resources per topic
_SEARCH_CONCURRENCY = 4     # bound concurrent web-search calls per roadmap
_URL_VERIFY_TIMEOUT = 6.0   # seconds per URL liveness check
_MAX_TITLE_LEN = 255        # matches LearningResource.title DB column
_MAX_URL_LEN = 500          # matches LearningResource.url DB column
_ALLOWED_RESOURCE_TYPES = {"article", "tutorial", "documentation", "video"}
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ── Retry decorator factory ───────────────────────────────────────────────────
# Retries on transient errors only; validation / auth errors are not retried.

_TRANSIENT_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
    httpx.TimeoutException,
    httpx.ConnectError,
)

_retry_transient = retry(
    retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,  # We handle the final exception ourselves
)


# ── Helper ────────────────────────────────────────────────────────────────────


def _parse_json(raw: str | None, context: str) -> Any:
    """Parse JSON string from an AI response; raise AIResponseError on failure."""
    if not raw:
        raise AIResponseError(f"Empty response from AI for {context}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIResponseError(
            f"Malformed JSON in AI response for {context}: {exc}"
        ) from exc


def _extract_json_object(text: str | None, context: str) -> Any:
    """Extract the first JSON object embedded in free-form model text.

    Web-search responses may wrap JSON in prose or code fences, so we slice
    from the first '{' to the last '}' before parsing.
    """
    if not text:
        raise AIResponseError(f"Empty response from AI for {context}")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AIResponseError(f"No JSON object found in AI response for {context}")
    return _parse_json(text[start : end + 1], context)


# ── OpenAI Provider ───────────────────────────────────────────────────────────


class OpenAIProvider:
    """Async OpenAI-backed implementation of AIProvider.

    Uses ``gpt-4o-mini`` by default for cost efficiency; override via
    ``model`` constructor argument.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float | None = None,
    ) -> None:
        self._model = model
        resolved_key = api_key or settings.openai_api_key
        resolved_timeout = timeout or float(settings.ai_timeout_seconds)
        self._client = AsyncOpenAI(
            api_key=resolved_key,
            timeout=resolved_timeout,
        )

    # ── Internal call helper ──────────────────────────────────────────────────

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI chat completions and return the assistant message text.

        Wraps tenacity retry inside this helper so that all public methods
        share a single retry policy without repeating the decorator.
        """

        async def _call_with_retry() -> str:
            last_exc: Exception | None = None
            for attempt in range(1, 4):  # up to 3 attempts
                try:
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                    )
                    content = response.choices[0].message.content
                    if content is None:
                        raise AIResponseError("OpenAI returned a null message content")
                    return content
                except (
                    openai.APITimeoutError,
                    httpx.TimeoutException,
                ) as exc:
                    last_exc = exc
                    logger.warning(
                        "OpenAI timeout on attempt %d/3: %s", attempt, exc
                    )
                    if attempt == 3:
                        raise AITimeoutError() from exc
                except (
                    openai.APIConnectionError,
                    openai.RateLimitError,
                    openai.InternalServerError,
                    httpx.ConnectError,
                ) as exc:
                    last_exc = exc
                    logger.warning(
                        "OpenAI unavailable on attempt %d/3: %s", attempt, exc
                    )
                    if attempt == 3:
                        raise AIUnavailableError() from exc
                except openai.AuthenticationError as exc:
                    # Non-transient: don't retry
                    raise AIUnavailableError(
                        "OpenAI authentication failed. Check OPENAI_API_KEY."
                    ) from exc
                except AIResponseError:
                    raise
                except Exception as exc:
                    raise AIResponseError(
                        f"Unexpected error during OpenAI call: {exc}"
                    ) from exc

                # Exponential back-off between attempts: 1s, 2s
                import asyncio
                await asyncio.sleep(2 ** (attempt - 1))

            # Should not reach here, but satisfy type checker
            raise AIUnavailableError() from last_exc

        return await _call_with_retry()

    # ── Public methods ────────────────────────────────────────────────────────

    async def analyze_resume(self, content: str, format: str) -> dict:
        """Extract structured information from resume text.

        Returns a dict with keys: skills, job_history, years_of_experience.
        """
        system = (
            "You are an expert resume parser. "
            "Extract information from the resume and return ONLY valid JSON "
            "with keys: skills (array of strings), job_history "
            "(array of {title, company, years}), years_of_experience (integer)."
        )
        user = f"Resume format: {format}\n\nResume content:\n{content}"
        raw = await self._chat(system, user)
        data = _parse_json(raw, "analyze_resume")
        if not isinstance(data, dict):
            raise AIResponseError("analyze_resume: expected a JSON object")
        return data

    async def identify_role_skills(self, role_title: str) -> list[SkillRequirement]:
        """Return at least 5 skills required for the given role."""
        system = (
            "You are a career coach with expertise across all professional fields — "
            "including but not limited to science, technology, engineering, medicine, "
            "law, finance, commerce, arts, design, education, social sciences, "
            "humanities, trades, and any other domain. "
            "Return ONLY valid JSON: an object with a 'skills' key containing "
            "an array of skill objects. Each object must have: "
            "skill_name (string), required_proficiency (beginner|intermediate|advanced), "
            "category (critical|important|nice-to-have). "
            "The skills must be realistic and specific to the role provided, "
            "regardless of industry or domain."
        )
        user = f"List the skills and competencies required for: {role_title}"
        raw = await self._chat(system, user)
        data = _parse_json(raw, "identify_role_skills")
        try:
            items: list[dict] = data.get("skills", data) if isinstance(data, dict) else data
            return [SkillRequirement(**item) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"identify_role_skills: invalid structure: {exc}"
            ) from exc

    async def analyze_skill_gaps(
        self,
        current_skills: list[Skill],
        target_skills: list[SkillRequirement],
    ) -> list[SkillGap]:
        """Compare user skills against target role requirements."""
        system = (
            "You are a skill gap analysis expert covering all professional domains — "
            "science, arts, commerce, technology, healthcare, law, education, trades, "
            "and any other field. "
            "Return ONLY valid JSON: an object with a 'gaps' key containing "
            "an array of gap objects. Each object must have: "
            "skill_name (string), category (critical|important|nice-to-have), "
            "current_proficiency (beginner|intermediate|advanced or null), "
            "required_proficiency (beginner|intermediate|advanced). "
            "Base your analysis purely on the skills and requirements provided, "
            "without assuming any particular industry."
        )
        current = [s.model_dump() for s in current_skills]
        target = [r.model_dump() for r in target_skills]
        user = (
            f"Current skills: {json.dumps(current)}\n"
            f"Target role requirements: {json.dumps(target)}\n"
            "Identify which skills are missing or insufficient."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "analyze_skill_gaps")
        try:
            items: list[dict] = data.get("gaps", data) if isinstance(data, dict) else data
            return [SkillGap(**item) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"analyze_skill_gaps: invalid structure: {exc}"
            ) from exc

    async def generate_roadmap(
        self,
        gaps: list[SkillGap],
        constraints: dict,
    ) -> list[RoadmapTopic]:
        """Generate an ordered learning roadmap for the given gaps.

        Two-stage pipeline:
          1. Structure — the model designs the topic graph (skills, categories,
             prerequisites, proficiency targets, hours, ordering) with NO
             resources. This is pure reasoning and does not touch the web.
          2. Resource curation — for each topic we run a live web search
             (Responses API ``web_search`` tool) to fetch real, currently-active
             study material, then verify every URL resolves before keeping it.
        """
        # ── Stage 1: structure only ────────────────────────────────────────
        structured = await self._generate_roadmap_structure(gaps, constraints)

        # ── Stage 2: web-grounded, verified resources (concurrent) ─────────
        semaphore = asyncio.Semaphore(_SEARCH_CONCURRENCY)

        async def _attach_resources(item: dict) -> None:
            async with semaphore:
                resources = await self._curate_resources(
                    skill_name=item["skill_name"],
                    proficiency=item.get("proficiency_target", "beginner"),
                    category=item.get("category", "important"),
                )
            item["resources"] = [r.model_dump() for r in resources]

        await asyncio.gather(*(_attach_resources(item) for item in structured))

        try:
            return [RoadmapTopic(**item) for item in structured]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"generate_roadmap: invalid structure: {exc}"
            ) from exc

    # ── Roadmap stage 1: structure ─────────────────────────────────────────

    async def _generate_roadmap_structure(
        self,
        gaps: list[SkillGap],
        constraints: dict,
    ) -> list[dict]:
        """Design the roadmap topic graph without resources (reasoning only)."""
        system = (
            "You are a learning roadmap designer. It is currently 2026. "
            "You work across ALL professional domains — science, technology, "
            "engineering, medicine, law, finance, commerce, arts, design, "
            "education, social sciences, humanities, trades, and any other field. "
            "Design a well-structured learning roadmap for the given skill gaps. "
            "Do NOT include learning resources or URLs — those are curated "
            "separately. Focus purely on structure and sequencing.\n\n"
            "Return ONLY valid JSON: an object with a 'topics' key containing an "
            "array of topic objects. Each object must have: "
            "id (UUID string), skill_name (string), "
            "category (critical|important|nice-to-have), "
            "proficiency_target (beginner|intermediate|advanced), "
            "prerequisites (array of UUID strings referencing other topic ids), "
            "estimated_hours (integer), order (integer starting at 1).\n\n"
            "STRUCTURE RULES:\n"
            "1. Break each skill gap into concrete, learnable topics. Split broad "
            "gaps into multiple sequential topics when it aids learning.\n"
            "2. Set prerequisites so foundational topics come before advanced ones. "
            "Use the ids of earlier topics.\n"
            "3. estimated_hours must be realistic for the proficiency target "
            "(typically 4-40 hours per topic).\n"
            "4. Order topics so prerequisites appear before dependents, and "
            "critical gaps before important before nice-to-have.\n"
            "5. proficiency_target should match the depth the role requires."
        )
        gap_data = [g.model_dump() for g in gaps]
        user = (
            f"Skill gaps: {json.dumps(gap_data)}\n"
            f"Constraints: {json.dumps(constraints)}\n"
            "Design the roadmap structure (no resources)."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "generate_roadmap_structure")
        items: list[dict] = (
            data.get("topics", data) if isinstance(data, dict) else data
        )
        if not isinstance(items, list) or not items:
            raise AIResponseError(
                "generate_roadmap_structure: expected a non-empty 'topics' array"
            )

        # Remap AI-generated ids to real UUIDs, keeping prerequisite refs consistent.
        id_mapping: dict[str, str] = {}
        for item in items:
            real_id = str(uuid.uuid4())
            id_mapping[str(item.get("id", ""))] = real_id
            item["id"] = real_id
        for item in items:
            item["prerequisites"] = [
                id_mapping[str(p)]
                for p in item.get("prerequisites", [])
                if str(p) in id_mapping
            ]
            item.pop("resources", None)  # ensure stage 2 owns resources
        return items

    # ── Roadmap stage 2: web-grounded resource curation ────────────────────

    async def _curate_resources(
        self,
        skill_name: str,
        proficiency: str,
        category: str,
    ) -> list[LearningResource]:
        """Return 2-3 real, verified, free learning resources for a topic.

        Uses a live web search, then verifies each URL resolves. Falls back to
        guaranteed-live search-portal links if too few resources survive.
        """
        try:
            candidates = await self._web_search_resources(skill_name, proficiency)
        except Exception as exc:  # never fail the whole roadmap on one topic
            logger.warning(
                "Resource web-search failed for %r: %s", skill_name, exc
            )
            candidates = []

        # Verify liveness and drop dead links; de-duplicate by URL.
        verified = await self._verify_urls(candidates)
        seen: set[str] = set()
        unique: list[LearningResource] = []
        for res in verified:
            key = (res.url or "").lower()
            if key and key in seen:
                continue
            seen.add(key)
            unique.append(res)

        # Guarantee the minimum with always-live fallback search links.
        if len(unique) < _MIN_RESOURCES:
            for fb in self._fallback_resources(skill_name):
                if (fb.url or "").lower() in seen:
                    continue
                unique.append(fb)
                if len(unique) >= _MIN_RESOURCES:
                    break

        return unique[:_TARGET_RESOURCES]

    async def _web_search_resources(
        self, skill_name: str, proficiency: str
    ) -> list[LearningResource]:
        """Search the live web for free study material for a single skill."""
        prompt = (
            "It is 2026. Use web search to find the best FREE, publicly "
            "accessible, and currently-active learning resources for the "
            f"skill: '{skill_name}' at {proficiency} level. "
            "Match the actual domain of the skill (do not default to software "
            "resources for non-tech skills). Prefer official documentation, "
            "reputable educational sites, university/open-courseware material, "
            "and established YouTube channels or playlists. Avoid paywalled "
            "content, Medium posts, and personal blogs that go stale.\n\n"
            f"Return {_TARGET_RESOURCES} resources as ONLY a JSON object: "
            '{"resources": [{"title": string, "type": '
            '"article"|"tutorial"|"documentation"|"video", "url": string}]}. '
            "Every url must be a real link you actually found via search."
        )
        raw = await self._respond_with_web_search(prompt)
        data = _extract_json_object(raw, "web_search_resources")
        items = data.get("resources", []) if isinstance(data, dict) else []
        resources: list[LearningResource] = []
        for item in items:
            res = self._normalize_resource(item)
            if res is not None:
                resources.append(res)
        return resources

    @staticmethod
    def _normalize_resource(item: dict) -> LearningResource | None:
        """Coerce a raw resource dict into a valid LearningResource, or None."""
        if not isinstance(item, dict):
            return None
        url = item.get("url")
        if not url or not isinstance(url, str) or not url.startswith("http"):
            return None
        if len(url) > _MAX_URL_LEN:
            return None  # can't safely truncate a URL; drop it
        rtype = str(item.get("type", "")).lower()
        if rtype in ("course", "book"):
            rtype = "article"
        if rtype not in _ALLOWED_RESOURCE_TYPES:
            rtype = "article"
        title = str(item.get("title") or "Untitled resource")[:_MAX_TITLE_LEN]
        return LearningResource(title=title, type=rtype, url=url)

    @staticmethod
    def _fallback_resources(skill_name: str) -> list[LearningResource]:
        """Guaranteed-live search-portal links used only to meet the minimum."""
        q = quote_plus(skill_name)
        return [
            LearningResource(
                title=f"{skill_name} — Wikipedia",
                type="article",
                url=f"https://en.wikipedia.org/w/index.php?search={q}",
            ),
            LearningResource(
                title=f"{skill_name} — video tutorials (YouTube)",
                type="video",
                url=f"https://www.youtube.com/results?search_query={q}+tutorial",
            ),
        ]

    async def _respond_with_web_search(self, prompt: str) -> str:
        """Call the Responses API with the web_search tool; return output text.

        Tries the GA ``web_search`` tool and falls back to the preview tool
        name if the account/model requires it. Shares the transient-retry
        behaviour of the chat helper.
        """
        tool_types = ("web_search", "web_search_preview")
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            for tool_type in tool_types:
                try:
                    response = await self._client.responses.create(
                        model=self._model,
                        tools=[{"type": tool_type}],
                        input=prompt,
                    )
                    return response.output_text or ""
                except openai.BadRequestError as exc:
                    # Likely an unsupported tool name — try the other variant.
                    last_exc = exc
                    logger.warning(
                        "web_search tool %r rejected: %s", tool_type, exc
                    )
                    continue
                except (openai.APITimeoutError, httpx.TimeoutException) as exc:
                    last_exc = exc
                    break  # retry outer loop
                except (
                    openai.APIConnectionError,
                    openai.RateLimitError,
                    openai.InternalServerError,
                    httpx.ConnectError,
                ) as exc:
                    last_exc = exc
                    break  # retry outer loop
                except openai.AuthenticationError as exc:
                    raise AIUnavailableError(
                        "OpenAI authentication failed. Check OPENAI_API_KEY."
                    ) from exc
            await asyncio.sleep(2 ** (attempt - 1))
        raise AIUnavailableError(
            f"web search unavailable after retries: {last_exc}"
        ) from last_exc

    @staticmethod
    async def _verify_urls(
        resources: list[LearningResource],
    ) -> list[LearningResource]:
        """Drop resources whose URL clearly does not resolve.

        Conservative by design: only links that fail to connect or return a
        definitive not-found status (404/410/451) are removed. Ambiguous
        results (timeouts, bot-blocking 403/405, etc.) are kept.
        """
        if not resources:
            return []

        _DEAD_STATUSES = {404, 410, 451}
        _RETRY_WITH_GET = {403, 405, 501, 999}

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_URL_VERIFY_TIMEOUT,
            headers={"User-Agent": _BROWSER_UA},
        ) as client:

            async def _check(res: LearningResource) -> LearningResource | None:
                if not res.url:
                    return None
                try:
                    resp = await client.head(res.url)
                    if resp.status_code in _RETRY_WITH_GET:
                        resp = await client.get(res.url)
                    if resp.status_code in _DEAD_STATUSES:
                        return None
                    return res
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    return None  # host unreachable / DNS failure → dead
                except Exception:
                    return res  # ambiguous → keep rather than lose a good link

            results = await asyncio.gather(*(_check(r) for r in resources))

        return [r for r in results if r is not None]

    async def generate_interview_questions(
        self,
        role: str,
        skills: list[str],
        difficulty: ProficiencyLevel,
    ) -> list[InterviewQuestion]:
        """Generate 5-20 mock interview questions for the given role."""
        system = (
            "You are an experienced interviewer and career coach covering ALL professional "
            "domains — science, technology, medicine, law, finance, commerce, arts, design, "
            "education, social sciences, trades, and any other field. "
            "Return ONLY valid JSON: an object with a 'questions' key containing "
            "an array of question objects. Each object must have: "
            "id (UUID string), question (string), "
            "category (knowledge|behavioral|case-study), "
            "difficulty (beginner|intermediate|advanced), "
            "model_answer (string), evaluation_criteria (array of strings, min 1). "
            "Category meanings: "
            "'knowledge' = domain-specific knowledge or conceptual questions relevant to the role "
            "(replaces 'technical' — applies to any field, e.g. legal principles, accounting rules, "
            "scientific concepts, design theory); "
            "'behavioral' = past experience, situational, soft-skills questions; "
            "'case-study' = scenario-based problem solving relevant to the role "
            "(e.g. a business case, a patient scenario, a legal scenario, an engineering problem). "
            "Include at least one question from each applicable category. "
            "Generate between 5 and 20 questions. "
            "All questions must be realistic and relevant to the specific role provided."
        )
        user = (
            f"Role: {role}\n"
            f"Relevant skills: {json.dumps(skills)}\n"
            f"Difficulty level: {difficulty}\n"
            "Generate mock interview questions appropriate for this role."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "generate_interview_questions")
        try:
            items: list[dict] = (
                data.get("questions", data) if isinstance(data, dict) else data
            )
            questions = []
            for item in items:
                # Normalise legacy category names from old DB rows
                cat_remap = {"technical": "knowledge", "system-design": "case-study"}
                if item.get("category") in cat_remap:
                    item["category"] = cat_remap[item["category"]]
                # Always generate a proper UUID regardless of what AI returns
                item["id"] = str(uuid.uuid4())
                questions.append(InterviewQuestion(**item))
            return questions
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"generate_interview_questions: invalid structure: {exc}"
            ) from exc

    async def evaluate_interview_answer(
        self,
        question: str,
        criteria: list[str],
        answer: str,
    ) -> AnswerFeedback:
        """Evaluate a user's answer and return structured feedback."""
        system = (
            "You are a rigorous interview coach providing constructive feedback. "
            "Return ONLY valid JSON with keys: "
            "strengths (array of strings), "
            "areas_for_improvement (array of strings), "
            "overall_assessment (string)."
        )
        user = (
            f"Question: {question}\n"
            f"Evaluation criteria: {json.dumps(criteria)}\n"
            f"Candidate answer: {answer}\n"
            "Evaluate the answer and provide feedback."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "evaluate_interview_answer")
        try:
            return AnswerFeedback(**data)
        except (TypeError, ValueError) as exc:
            raise AIResponseError(
                f"evaluate_interview_answer: invalid structure: {exc}"
            ) from exc

    async def suggest_projects(
        self,
        skills: list[str],
        level: ProficiencyLevel,
    ) -> list[ProjectSuggestion]:
        """Suggest a balanced portfolio of nine real-world projects for 2026."""
        system = (
            "You are a project mentor covering ALL professional domains — "
            "science, technology, medicine, law, finance, commerce, arts, design, "
            "education, social sciences, trades, and any other field. "
            "Identify concrete, current problems that people or organizations face "
            "in 2026 in the actual domain of the supplied skills. Avoid generic "
            "practice projects, clones, toy apps, and hypothetical problems.\n\n"
            "Return ONLY valid JSON: an object with a 'projects' key containing "
            "exactly 9 distinct project objects, ordered as 3 beginner, 3 "
            "intermediate, and 3 advanced projects. Each object must have: "
            "id (UUID string), title (string), objectives (array of strings), "
            "deliverables (array of strings), technologies (array of strings — "
            "use tools, methods, materials, equipment, frameworks, or media "
            "appropriate to the domain), estimated_weeks (integer 1-4), and "
            "complexity (beginner|intermediate|advanced).\n\n"
            "Every project must solve a different real-world 2026 problem and "
            "produce a usable outcome for a clearly identifiable beneficiary. "
            "The first objective must start exactly with '2026 problem:' and "
            "plainly state the problem and who experiences it. Include at least "
            "2 objectives, 2 concrete deliverables, and 2 relevant "
            "technologies/tools/methods per project. Beginner projects should be "
            "small but useful; intermediate projects should integrate multiple "
            "skills and real constraints; advanced projects should address "
            "system-level concerns such as scale, reliability, security, "
            "accessibility, ethics, or measurable impact, while remaining scoped "
            "as a 1-4 week prototype."
        )
        user = (
            f"Skills: {json.dumps(skills)}\n"
            f"Learner's current skill level: {level}\n"
            "Use the learner level only to tailor explanations and achievable "
            "scope; do not change the required 3/3/3 difficulty distribution. "
            "Prefer problems with clear relevance in 2026 and make each title "
            "specific to the outcome, not the technology being practised."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "suggest_projects")
        try:
            items: list[dict] = (
                data.get("projects", data) if isinstance(data, dict) else data
            )
            projects: list[ProjectSuggestion] = []
            for item in items:
                # Always generate a proper UUID regardless of what AI returns.
                item["id"] = str(uuid.uuid4())
                projects.append(ProjectSuggestion(**item))

            required_counts = {
                "beginner": 3,
                "intermediate": 3,
                "advanced": 3,
            }
            actual_counts = {name: 0 for name in required_counts}
            for project in projects:
                actual_counts[project.complexity] += 1
                if (
                    len(project.objectives) < 2
                    or len(project.deliverables) < 2
                    or len(project.technologies) < 2
                ):
                    raise ValueError(
                        f"project '{project.title}' must include at least two "
                        "objectives, deliverables, and technologies/tools"
                    )
                if not project.objectives[0].strip().lower().startswith(
                    "2026 problem:"
                ):
                    raise ValueError(
                        f"project '{project.title}' does not identify its "
                        "2026 problem"
                    )

            if len(projects) != 9 or actual_counts != required_counts:
                raise ValueError(
                    "expected exactly 9 projects with 3 beginner, 3 intermediate, "
                    f"and 3 advanced; received {len(projects)} with {actual_counts}"
                )
            if len({p.title.strip().casefold() for p in projects}) != 9:
                raise ValueError("project titles must be distinct")
            return projects
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"suggest_projects: invalid structure: {exc}"
            ) from exc
