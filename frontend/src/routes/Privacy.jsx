import LegalLayout, { List, P, Section } from "@/components/auth/LegalLayout"

export default function Privacy() {
  return (
    <LegalLayout title="Privacy Policy">
      <P>
        This Privacy Policy explains how DoxaEd ("DoxaEd", "we", "us") collects, uses, and
        protects personal information when you use DoxaEd OMR (the "Service"), our platform
        for generating, scanning, and auto-grading OMR exam sheets. It also explains the
        rights available to you and to the students whose data you process. For data you
        upload about your students, you are the controller and we act as your processor.
      </P>

      <Section heading="1. Information we collect">
        <P>We collect the following categories of information:</P>
        <List
          items={[
            "Account data: your name, email address, and authentication details. If you sign in with Google, we receive your email, name, and a verified-email flag from Google — we never receive your Google password.",
            "Organisation data: organisation names, member roles, and invitations you create.",
            "Student data you upload: student names, roll numbers, roster entries, scanned answer sheets, exam responses, and computed scores. Names and roll numbers are personally identifiable information (PII) and are stored encrypted at rest.",
            "Usage and technical data: log entries, IP address, device/browser information, and audit records of actions taken in the Service.",
            "Payment data: subscription and billing records. Card processing is handled by Razorpay; we do not store full card numbers.",
          ]}
        />
      </Section>

      <Section heading="2. How we use information">
        <List
          items={[
            "To provide the Service: generating sheets, running server-side grading, producing results and analytics, and operating public result links you choose to publish.",
            "To secure the Service: authentication, abuse prevention, rate limiting, and audit logging.",
            "To support you: responding to enquiries and providing customer support.",
            "To process payments and manage subscriptions.",
            "To comply with legal obligations and enforce our Terms.",
          ]}
        />
        <P>
          We do not sell personal information, and we do not use student data for
          advertising.
        </P>
      </Section>

      <Section heading="3. Lawful basis for processing">
        <P>
          Where data-protection law requires a lawful basis, we rely on: performance of a
          contract (to provide the Service to you); our legitimate interests (to secure and
          improve the Service); your consent where applicable; and compliance with legal
          obligations. For student data, you are responsible for establishing the lawful
          basis and obtaining any consents required from students, parents, or guardians.
        </P>
      </Section>

      <Section heading="4. Sub-processors">
        <P>
          We use a limited number of trusted service providers to operate the Service,
          including a cloud hosting provider, our payment processor (Razorpay), and, where
          you enable Google Sign-In, Google for authentication. A current list of
          sub-processors will be maintained at [sub-processor list URL to be finalised
          before production]. We require sub-processors to protect personal information
          consistent with this Policy.
        </P>
      </Section>

      <Section heading="5. Data retention">
        <P>
          We retain personal information for as long as your account is active and as
          needed to provide the Service. You can delete classes, rosters, tests, and
          results from within the Service. When you close your account, we delete or
          anonymise personal information within a reasonable period, except where we are
          required to retain it to comply with legal, accounting, or security obligations.
          Backups are purged on a rolling schedule.
        </P>
      </Section>

      <Section heading="6. Security and encryption">
        <List
          items={[
            "Student PII (such as names and roll numbers) is encrypted at rest using application-level field encryption.",
            "Data is transmitted over encrypted connections (HTTPS/TLS).",
            "Access is isolated per owner and per organisation, and protected by authentication, password hashing, login-attempt lockout, and rate limiting.",
            "Grading runs server-side and produces auditable records; low-confidence reads are queued for human review rather than guessed.",
          ]}
        />
        <P>
          No system is perfectly secure, but we work to protect your information using
          appropriate technical and organisational measures.
        </P>
      </Section>

      <Section heading="7. Your rights">
        <P>
          Depending on your jurisdiction, you may have rights to access, correct, export,
          or delete your personal information, to object to or restrict certain
          processing, and to withdraw consent. To exercise these rights with respect to
          your own account data, contact us at doxaed@gmail.com. For student data we hold
          on your behalf, requests from students, parents, or guardians should be directed
          to you as the controller; we will assist you in responding to such requests.
        </P>
      </Section>

      <Section heading="8. Children's data">
        <P>
          The Service is intended for use by teachers, tutors, coaching centres, schools,
          and organisations &mdash; not directly by children. Where the Service is used to
          process data about students who are minors, you are responsible for obtaining any
          consents required from parents or guardians and for ensuring such processing is
          lawful. We handle student data only on your documented instructions as your
          processor.
        </P>
      </Section>

      <Section heading="9. International transfers">
        <P>
          Your information may be processed in countries other than your own. Where we
          transfer personal information across borders, we take steps to ensure it remains
          protected consistent with this Policy and applicable law. Specific transfer
          mechanisms will be confirmed by legal counsel before production.
        </P>
      </Section>

      <Section heading="10. Changes to this Policy">
        <P>
          We may update this Privacy Policy from time to time. When we make material
          changes we will update the "last updated" date above and, where appropriate,
          provide additional notice. Your continued use of the Service after changes take
          effect constitutes acceptance of the revised Policy.
        </P>
      </Section>

      <Section heading="11. Contact">
        <P>
          Questions about this Policy or our handling of personal information? Contact us
          at{" "}
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
