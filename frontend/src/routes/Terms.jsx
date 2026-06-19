import LegalLayout, { List, P, Section } from "@/components/auth/LegalLayout"

export default function Terms() {
  return (
    <LegalLayout title="Terms of Service">
      <P>
        These Terms of Service ("Terms") govern your access to and use of DoxaEd OMR
        (the "Service"), an optical-mark-recognition (OMR) platform for generating exam
        answer sheets, scanning them, and producing auto-graded results and analytics.
        The Service is operated by DoxaEd ("DoxaEd", "we", "us"). By creating an account
        or using the Service, you agree to these Terms. If you do not agree, do not use
        the Service.
      </P>

      <Section heading="1. Acceptance and eligibility">
        <P>
          By accessing the Service you confirm that you are at least 18 years old (or the
          age of majority in your jurisdiction) and have the authority to enter into these
          Terms on behalf of yourself and any organisation you represent. If you use the
          Service on behalf of an organisation, you accept these Terms for that
          organisation and warrant that you may bind it.
        </P>
      </Section>

      <Section heading="2. Accounts and security">
        <List
          items={[
            "You are responsible for the accuracy of the information you provide and for keeping your account credentials confidential.",
            "You are responsible for all activity that occurs under your account, including activity by members you invite to your organisation.",
            "You must notify us promptly at doxaed@gmail.com of any unauthorised use of your account or any other security incident you become aware of.",
            "We may suspend or disable accounts that we reasonably believe have been compromised or are being used in violation of these Terms.",
          ]}
        />
      </Section>

      <Section heading="3. Acceptable use">
        <P>You agree not to, and not to permit any user to:</P>
        <List
          items={[
            "Use the Service for any unlawful purpose or in violation of any applicable law, regulation, or examination-board rule;",
            "Upload content you do not have the right to process, or that infringes the rights of any third party;",
            "Attempt to gain unauthorised access to the Service, other accounts, or any system or network connected to the Service;",
            "Interfere with or disrupt the integrity or performance of the Service, including by probing, scanning, or load-testing without our written consent;",
            "Reverse engineer, decompile, or otherwise attempt to derive the source code of the Service except to the extent permitted by law;",
            "Resell, sublicense, or provide the Service to third parties except through the organisation features we provide.",
          ]}
        />
      </Section>

      <Section heading="4. Student data and your responsibilities">
        <P>
          The Service is designed to process student information &mdash; including names,
          roll numbers, exam responses, and scores &mdash; on your behalf. You (and your
          organisation) act as the controller of that information; DoxaEd acts as a
          processor. You are solely responsible for:
        </P>
        <List
          items={[
            "Having a lawful basis to collect and process student data, and obtaining any consents required (including from parents or guardians where students are minors);",
            "Ensuring that the data you upload is accurate and that you are authorised to upload it;",
            "Honouring requests from students, parents, or guardians regarding their data, and for disclosures you make through any public result links you choose to publish;",
            "Complying with all education, privacy, and data-protection laws that apply to you.",
          ]}
        />
        <P>
          We store student personally identifiable information in encrypted form and
          isolate data per owner and per organisation. Our handling of personal data is
          described in our Privacy Policy.
        </P>
      </Section>

      <Section heading="5. Intellectual property">
        <P>
          The Service, including its software, design, templates, and documentation, is
          owned by DoxaEd and protected by intellectual-property laws. We grant you a
          limited, non-exclusive, non-transferable, revocable licence to use the Service
          in accordance with these Terms. You retain all rights to the exam content,
          rosters, and student data you upload ("Your Content"); you grant us a licence to
          host and process Your Content solely to provide and improve the Service.
        </P>
      </Section>

      <Section heading="6. Payment and subscriptions">
        <List
          items={[
            "Paid plans and their limits are described at the point of purchase. Payments are processed by our payment provider, Razorpay; we do not store your full card details.",
            "Fees are billed in advance for the applicable subscription period and, except where required by law, are non-refundable.",
            "We may change plan pricing or features on prospective notice. Continued use after a change takes effect constitutes acceptance of the new terms.",
            "If a payment fails or a subscription lapses, we may downgrade or suspend access to paid features while retaining your data for a reasonable period.",
          ]}
        />
      </Section>

      <Section heading="7. Service availability and disclaimers">
        <P>
          The Service is provided "as is" and "as available" without warranties of any
          kind, whether express or implied, including warranties of merchantability,
          fitness for a particular purpose, and non-infringement. Automated grading
          depends on the quality of the scanned sheets and the answer keys you provide;
          you are responsible for reviewing results before relying on them. Low-confidence
          reads are routed to a review queue and are never silently guessed, but you
          remain responsible for verifying outcomes.
        </P>
      </Section>

      <Section heading="8. Limitation of liability">
        <P>
          To the maximum extent permitted by law, DoxaEd and its suppliers will not be
          liable for any indirect, incidental, special, consequential, or punitive
          damages, or any loss of data, profits, or goodwill, arising out of or relating
          to your use of the Service. Our aggregate liability for any claim relating to
          the Service will not exceed the amount you paid to us for the Service in the
          twelve (12) months preceding the event giving rise to the claim.
        </P>
      </Section>

      <Section heading="9. Termination">
        <P>
          You may stop using the Service and close your account at any time. We may
          suspend or terminate your access if you materially breach these Terms, if
          required by law, or to protect the Service or other users. On termination, your
          right to use the Service ends; we will handle your data in accordance with our
          Privacy Policy and applicable retention requirements.
        </P>
      </Section>

      <Section heading="10. Changes to these Terms">
        <P>
          We may update these Terms from time to time. When we make material changes we
          will update the "last updated" date above and, where appropriate, provide
          additional notice. Your continued use of the Service after changes take effect
          constitutes acceptance of the revised Terms.
        </P>
      </Section>

      <Section heading="11. Governing law">
        <P>
          These Terms are governed by the laws of [jurisdiction to be finalised by legal
          counsel], without regard to conflict-of-laws principles. The courts of that
          jurisdiction will have exclusive jurisdiction over any dispute arising out of or
          relating to these Terms or the Service.
        </P>
      </Section>

      <Section heading="12. Contact">
        <P>
          Questions about these Terms? Contact us at{" "}
          <a
            href="mailto:doxaed@gmail.com"
            className="text-primary underline-offset-4 hover:underline"
          >
            doxaed@gmail.com
          </a>
          .
        </P>
      </Section>
    </LegalLayout>
  )
}
