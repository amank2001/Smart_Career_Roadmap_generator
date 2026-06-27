import Link from "next/link";

const STEPS = [
  {
    number: 1,
    title: "Create Your Profile",
    description: "Add your skills, experience, and career background — or upload your resume for auto-extraction.",
    href: "/profile",
    color: "bg-blue-500",
  },
  {
    number: 2,
    title: "Select Target Role",
    description: "Choose your desired career destination and review the required skills.",
    href: "/target-role",
    color: "bg-purple-500",
  },
  {
    number: 3,
    title: "Skill Gap Analysis",
    description: "See where you stand vs. where you need to be, categorized by priority.",
    href: "/skill-gap",
    color: "bg-red-500",
  },
  {
    number: 4,
    title: "Learning Roadmap",
    description: "Get an AI-generated study plan with topics, timelines, and resource recommendations.",
    href: "/roadmap",
    color: "bg-orange-500",
  },
  {
    number: 5,
    title: "Weekly Plans",
    description: "Break your roadmap into actionable weekly tasks you can check off.",
    href: "/weekly-plans",
    color: "bg-amber-500",
  },
  {
    number: 6,
    title: "Projects",
    description: "Practice with hands-on project suggestions tailored to your learning goals.",
    href: "/projects",
    color: "bg-green-500",
  },
  {
    number: 7,
    title: "Interview Prep",
    description: "Generate mock interview questions and get AI feedback on your answers.",
    href: "/interview",
    color: "bg-teal-500",
  },
  {
    number: 8,
    title: "Track Progress",
    description: "Monitor your overall completion, milestones, and skills acquired.",
    href: "/progress",
    color: "bg-indigo-500",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      {/* Hero section */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
          Smart Career Roadmap Generator
        </h1>
        <p className="mt-3 text-lg text-gray-600">
          Plan your career transition with AI-powered roadmaps, personalized learning plans, and interview preparation.
        </p>
      </div>

      {/* Getting started CTA */}
      <div className="flex justify-center gap-4">
        <Link
          href="/profile"
          className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Get Started
        </Link>
        <Link
          href="/progress"
          className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          View Progress
        </Link>
      </div>

      {/* Steps grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step) => (
          <Link
            key={step.href}
            href={step.href}
            className="group rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-indigo-200 hover:shadow-md"
          >
            <div className="flex items-center gap-3">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white ${step.color}`}
              >
                {step.number}
              </span>
              <h3 className="text-sm font-semibold text-gray-900 group-hover:text-indigo-700">
                {step.title}
              </h3>
            </div>
            <p className="mt-3 text-xs text-gray-600 leading-relaxed">
              {step.description}
            </p>
          </Link>
        ))}
      </div>

      {/* How it works */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">How It Works</h2>
        <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
              <svg className="h-6 w-6 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-medium text-gray-900">Tell Us About You</h3>
            <p className="mt-1 text-xs text-gray-600">
              Share your current skills and choose your target career role.
            </p>
          </div>
          <div className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
              <svg className="h-6 w-6 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-medium text-gray-900">AI Generates Your Plan</h3>
            <p className="mt-1 text-xs text-gray-600">
              Get a personalized roadmap with weekly tasks and project ideas.
            </p>
          </div>
          <div className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
              <svg className="h-6 w-6 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-medium text-gray-900">Learn &amp; Track Progress</h3>
            <p className="mt-1 text-xs text-gray-600">
              Follow your plan, practice interviews, and watch your skills grow.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
