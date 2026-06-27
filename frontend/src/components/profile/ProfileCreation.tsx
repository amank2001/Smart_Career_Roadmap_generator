"use client";

import { useState } from "react";
import { ProfileForm } from "./ProfileForm";
import { ResumeUpload } from "./ResumeUpload";
import { ResumeDataConfirmation } from "./ResumeDataConfirmation";
import type { ResumeAnalysisResult, CreateProfileInput } from "@/lib/api";
import { createProfile, ApiError } from "@/lib/api";

type Step = "form" | "resume-confirm";

export function ProfileCreation() {
  const [step, setStep] = useState<Step>("form");
  const [resumeData, setResumeData] = useState<ResumeAnalysisResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

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
      setIsSuccess(true);
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

  if (isSuccess) {
    return (
      <div
        className="rounded-lg border border-green-200 bg-green-50 p-6 text-center"
        role="status"
        aria-live="polite"
      >
        <h2 className="text-xl font-semibold text-green-800">Profile Created Successfully!</h2>
        <p className="mt-2 text-green-700">
          Your profile has been saved. You can now proceed to select your target role.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {step === "form" && (
        <>
          <section aria-labelledby="profile-form-heading">
            <h2 id="profile-form-heading" className="mb-4 text-xl font-semibold text-gray-800">
              Create Your Profile
            </h2>
            <ProfileForm
              onSubmit={handleSubmitProfile}
              isSubmitting={isSubmitting}
              initialData={
                resumeData?.extracted_data
                  ? {
                      currentJobTitle: resumeData.extracted_data.current_job_title ?? "",
                      yearsOfExperience: resumeData.extracted_data.years_of_experience ?? 0,
                      skills: resumeData.extracted_data.skills ?? [],
                    }
                  : undefined
              }
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
