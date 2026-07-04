"use client";

import { useState } from "react";
import { ProfileForm } from "./ProfileForm";
import { ResumeUpload } from "./ResumeUpload";
import { ResumeDataConfirmation } from "./ResumeDataConfirmation";
import type { ResumeAnalysisResult, CreateProfileInput } from "@/lib/api";
import { createProfile, ApiError } from "@/lib/api";
import { useAppData } from "@/context/AppDataContext";

type Step = "form" | "resume-confirm";

export function ProfileCreation() {
  const { profile, isLoadingProfile, refreshProfile } = useAppData();

  const [step, setStep] = useState<Step>("form");
  const [resumeData, setResumeData] = useState<ResumeAnalysisResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Show loading skeleton while we check for an existing profile
  if (isLoadingProfile) {
    return (
      <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
        <div className="text-center">
          <div
            className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
            aria-hidden="true"
          />
          <p className="mt-3 text-sm text-gray-600">Loading your profile...</p>
        </div>
      </div>
    );
  }

  // If a profile exists and we're not in edit mode, show the summary view
  if (profile && !isEditing && !isSuccess) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-green-200 bg-green-50 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-green-800">Profile</h2>
              <p className="mt-1 text-sm text-green-700">
                Your profile is set up and ready.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="rounded-md border border-green-300 bg-white px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              Edit Profile
            </button>
          </div>
        </div>

        {/* Profile details card */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4 shadow-sm">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Current Job Title
              </p>
              <p className="mt-1 text-sm font-semibold text-gray-900">
                {profile.current_job_title || "—"}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Years of Experience
              </p>
              <p className="mt-1 text-sm font-semibold text-gray-900">
                {profile.years_of_experience ?? 0}
              </p>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Skills ({profile.skills.length})
            </p>
            {profile.skills.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {profile.skills.map((skill) => (
                  <span
                    key={skill.name}
                    className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-800"
                  >
                    {skill.name}
                    {skill.proficiency_level && (
                      <span className="ml-1 text-indigo-500">
                        · {skill.proficiency_level}
                      </span>
                    )}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-sm text-gray-500">No skills added yet.</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Post-save success state
  if (isSuccess) {
    return (
      <div className="space-y-6">
        <div
          className="rounded-lg border border-green-200 bg-green-50 p-6 text-center"
          role="status"
          aria-live="polite"
        >
          <h2 className="text-xl font-semibold text-green-800">
            Profile {profile ? "Updated" : "Created"} Successfully!
          </h2>
          <p className="mt-2 text-green-700">
            Your profile has been saved. You can now proceed to select your target role.
          </p>
          <button
            type="button"
            onClick={() => {
              setIsSuccess(false);
              setIsEditing(false);
            }}
            className="mt-4 rounded-md border border-green-300 bg-white px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            View Profile
          </button>
        </div>
      </div>
    );
  }

  function handleResumeExtracted(result: ResumeAnalysisResult) {
    if (result.success && result.extracted_data) {
      setResumeData(result);
      setStep("resume-confirm");
    }
  }

  function handleBackToForm() {
    setStep("form");
  }

  async function handleSubmitProfile(data: CreateProfileInput) {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await createProfile(data);
      await refreshProfile();
      setIsSuccess(true);
      setIsEditing(false);
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.userMessage);
      } else {
        setSubmitError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // Build initial data for the form:
  // Priority: resume-extracted data > existing profile > empty
  const formInitialData = resumeData?.extracted_data
    ? {
        currentJobTitle: resumeData.extracted_data.current_job_title ?? "",
        yearsOfExperience: resumeData.extracted_data.years_of_experience ?? 0,
        skills: resumeData.extracted_data.skills ?? [],
      }
    : profile
    ? {
        currentJobTitle: profile.current_job_title,
        yearsOfExperience: profile.years_of_experience,
        skills: profile.skills.map((s) => s.name),
      }
    : undefined;

  return (
    <div className="space-y-8">
      {/* Back button when editing an existing profile */}
      {isEditing && (
        <button
          type="button"
          onClick={() => {
            setIsEditing(false);
            setStep("form");
            setSubmitError(null);
          }}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
        >
          ← Back to profile
        </button>
      )}

      {step === "form" && (
        <>
          <section aria-labelledby="profile-form-heading">
            <h2 id="profile-form-heading" className="mb-4 text-xl font-semibold text-gray-800">
              {isEditing ? "Edit Your Profile" : "Create Your Profile"}
            </h2>
            <ProfileForm
              onSubmit={handleSubmitProfile}
              isSubmitting={isSubmitting}
              initialData={formInitialData}
              submitLabel={isEditing ? "Save Changes" : undefined}
            />
            {submitError && (
              <div
                className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                role="alert"
              >
                {submitError}
              </div>
            )}
          </section>

          <section aria-labelledby="resume-upload-heading">
            <h2 id="resume-upload-heading" className="mb-4 text-xl font-semibold text-gray-800">
              Or Upload Your Resume
            </h2>
            <p className="mb-4 text-sm text-gray-600">
              Upload your resume to automatically extract your skills and experience.
            </p>
            <ResumeUpload onExtracted={handleResumeExtracted} />
          </section>
        </>
      )}

      {step === "resume-confirm" && resumeData?.extracted_data && (
        <ResumeDataConfirmation
          extractedData={resumeData.extracted_data}
          onConfirm={handleSubmitProfile}
          onBack={handleBackToForm}
          isSubmitting={isSubmitting}
        />
      )}

      {step === "resume-confirm" && submitError && (
        <div
          className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {submitError}
        </div>
      )}
    </div>
  );
}
