# OMRFlow Phase 1 (Accounts) Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD. Steps use `- [ ]` checkboxes.
> **Repo:** standalone repo at `projects/omr.doxaed.com/` (own `.git`). Paths below are
> RELATIVE TO THAT REPO ROOT (`backend/...`, `frontend/...`). Commit to THIS repo (run git
> from inside `projects/omr.doxaed.com/`), branch `phase-1`. Do NOT commit to the workspace repo.

**Goal:** Email/password accounts — registration, email verification, login/logout, password
reset, and profile — secured with Argon2 (already set), JWT, scoped throttling, and the global
owner-scope permission, with a React auth UI on shadcn.

**Architecture:** Hand-rolled DRF views/serializers under `/api/v1/auth/`. Email verification &
password reset use Django's `default_token_generator` + urlsafe-base64 uid; emails are sent via
the console backend in dev and contain links to frontend routes that POST the uid+token back.
Logout blacklists the refresh token (simplejwt token_blacklist). The React SPA gets an
`AuthProvider` (tokens in localStorage + current user) and a `ProtectedRoute`.

**Tech Stack:** Django 5 + DRF + djangorestframework-simplejwt (+ token_blacklist) + Django core
email/token utils. React (Vite, JS) + shadcn `form` (react-hook-form + zod) + axios.

## Locked decisions
- **D1** Hand-rolled DRF auth (no djoser/dj-rest-auth) — coherent with Phase 0, fully testable.
- **D2** Dev email = console backend (`EMAIL_BACKEND` env-driven). Verify/reset use
  `django.contrib.auth.tokens.default_token_generator` + `urlsafe_base64_encode(uid)`. Email
  links point to `FRONTEND_URL` routes (`/verify-email`, `/reset-password`).
- **D3** Registration creates an ACTIVE user with `is_email_verified=False`. Login is allowed
  pre-verification (verification is a tracked flag, not a Phase-1 login gate). Documented; a
  hard gate can be added later if the product needs it.
- **D4** Logout = blacklist the provided refresh token (add `token_blacklist` app + migrate).
- **D5** Brute-force protection = DRF `ScopedRateThrottle` on login/register/password-reset
  (`5/min` each). Full account-lockout (django-axes) is deferred to Phase 8 hardening.
- **D6** Profile endpoint = `GET`/`PATCH /api/v1/auth/me/`.
- **D7** EVERY public auth endpoint sets `permission_classes = [AllowAny]` (the global default is
  `IsInScope`, which requires auth — forgetting this silently 401s). `me/` and `logout/` require auth.
- **D8** Frontend: `AuthProvider` context (access+refresh in localStorage, current user from
  `me/`), `ProtectedRoute`, shadcn-form screens; password-reset responses never reveal whether
  an email exists (no user enumeration).

## Endpoint contracts (all under `/api/v1/auth/`, trailing slashes)
- `POST register/` `{email, password, full_name?}` → `201 {id,email,full_name,is_email_verified}`; sends verify email.
- `POST verify-email/` `{uid, token}` → `200 {detail}` (sets `is_email_verified=True`); invalid → `400`.
- `POST login/` `{email, password}` → `200 {access, refresh, user}`; bad creds → `401`.
- `POST logout/` `{refresh}` (auth required) → `205`; blacklists the refresh token.
- `POST password-reset/` `{email}` → `200 {detail}` always (no enumeration); sends email if user exists.
- `POST password-reset-confirm/` `{uid, token, new_password}` → `200 {detail}`; invalid → `400`.
- `GET/PATCH me/` (auth required) → `200 {id,email,full_name,is_email_verified}`.
- (Phase 0 `token/` + `token/refresh/` remain.)

## File structure (in `backend/accounts/`)
- `serializers.py` — RegisterSerializer, LoginSerializer, MeSerializer, PasswordReset*Serializers.
- `tokens.py` — helpers: `make_uid_token(user)`, `read_uid_token(uid, token)`.
- `emails.py` — `send_verification_email(user, request)`, `send_password_reset_email(user, request)`.
- `views.py` — the 7 auth views.
- `urls.py` — auth routes (included from `config/urls.py`).
- `tests/` (or `tests_auth.py`) — TDD tests per task.
Frontend (`frontend/src/`): `auth/AuthContext.jsx`, `auth/ProtectedRoute.jsx`, additions to
`api/client.js`, and `routes/{Register,Login,VerifyEmail,ForgotPassword,ResetPassword,Profile}.jsx`.

---

## Task 1: Settings — email, FRONTEND_URL, token_blacklist, throttle scopes

**Files:** `backend/config/settings.py`, `backend/.env` + `.env.example`

- [ ] **Step 1:** Add to `INSTALLED_APPS` (after `rest_framework_simplejwt`... it's not listed; add it): append `"rest_framework_simplejwt.token_blacklist",`.
- [ ] **Step 2:** Add settings (anywhere sensible):
```python
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="OMRFlow <no-reply@omrflow.local>")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
```
Add to `SIMPLE_JWT`: `"BLACKLIST_AFTER_ROTATION": True,`.
Add scoped throttle rates into `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`: `"login": "5/min", "register": "5/min", "password_reset": "5/min"`. Ensure `ScopedRateThrottle` is available (DRF includes it; views set `throttle_scope`).
- [ ] **Step 3:** Add to `backend/.env` and `.env.example`: `FRONTEND_URL=http://localhost:5173` (and optionally `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`).
- [ ] **Step 4:** `.\.venv\Scripts\python.exe manage.py migrate` (creates token_blacklist tables). `manage.py check` clean.
- [ ] **Step 5:** Commit (from `projects/omr.doxaed.com/`): `git add backend/config/settings.py backend/.env.example && git commit -m "feat(accounts): settings for email, frontend URL, JWT blacklist, throttles"`.

## Task 2: Registration (TDD)

**Files:** `backend/accounts/serializers.py`, `tokens.py`, `emails.py`, `views.py`, `urls.py`, `config/urls.py`, `accounts/tests_auth.py`

- [ ] **Step 1 (red):** `backend/accounts/tests_auth.py`:
```python
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    def test_register_creates_unverified_user_and_sends_email(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "new@example.com", "password": "Str0ng!pass", "full_name": "New User",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.check_password("Str0ng!pass"))
        self.assertEqual(len(mail.outbox), 1)

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@example.com", password="x12345!!")
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "dup@example.com", "password": "Str0ng!pass",
        }, format="json")
        self.assertEqual(resp.status_code, 400)
```
- [ ] **Step 2:** Run `manage.py test accounts.tests_auth.RegisterTests` → FAIL (404/no view).
- [ ] **Step 3 (impl):** `backend/accounts/tokens.py`:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


def make_uid_token(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def read_uid_token(uid, token):
    try:
        pk = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None
    return user if default_token_generator.check_token(user, token) else None
```
`backend/accounts/emails.py`:
```python
from django.conf import settings
from django.core.mail import send_mail

from .tokens import make_uid_token


def _send(user, subject, path):
    uid, token = make_uid_token(user)
    link = f"{settings.FRONTEND_URL}{path}?uid={uid}&token={token}"
    send_mail(subject, f"Open this link:\n{link}\n", settings.DEFAULT_FROM_EMAIL, [user.email])
    return uid, token


def send_verification_email(user):
    return _send(user, "Verify your OMRFlow email", "/verify-email")


def send_password_reset_email(user):
    return _send(user, "Reset your OMRFlow password", "/reset-password")
```
`backend/accounts/serializers.py` (RegisterSerializer; others added in later tasks):
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "full_name", "is_email_verified")
        read_only_fields = ("id", "is_email_verified")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
```
`backend/accounts/views.py`:
```python
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .emails import send_verification_email
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user)
```
`backend/accounts/urls.py`:
```python
from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
]
```
In `backend/config/urls.py`, add: `path("api/v1/auth/", include("accounts.urls"))` (import `include`). Keep the existing token routes (they can stay as explicit paths or move into accounts.urls — keep them where they are).
- [ ] **Step 4:** Run the test → PASS.
- [ ] **Step 5:** Commit: `git add backend/accounts backend/config/urls.py && git commit -m "feat(accounts): registration endpoint + email verification mail"`.

## Task 3: Email verification (TDD)
**Files:** `views.py`, `urls.py`, `tests_auth.py`
- [ ] **Step 1 (red):** add test:
```python
from accounts.tokens import make_uid_token

class VerifyEmailTests(APITestCase):
    def test_verify_marks_user_verified(self):
        u = User.objects.create_user(email="v@example.com", password="Str0ng!pass")
        uid, token = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": token}, format="json")
        self.assertEqual(resp.status_code, 200)
        u.refresh_from_db(); self.assertTrue(u.is_email_verified)

    def test_verify_bad_token_400(self):
        u = User.objects.create_user(email="v2@example.com", password="Str0ng!pass")
        uid, _ = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/verify-email/", {"uid": uid, "token": "bad"}, format="json")
        self.assertEqual(resp.status_code, 400)
```
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3 (impl):** add to `views.py`:
```python
from rest_framework.views import APIView
from .tokens import read_uid_token


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = read_uid_token(request.data.get("uid"), request.data.get("token"))
        if user is None:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified."})
```
Add url: `path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email")`.
- [ ] **Step 4:** run → PASS.  **Step 5:** commit `feat(accounts): email verification endpoint`.

## Task 4: Login (TDD)
**Files:** `serializers.py`, `views.py`, `urls.py`, `tests_auth.py`
- [ ] **Step 1 (red):** test login returns access+refresh+user for good creds; 401 for bad:
```python
class LoginTests(APITestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="l@example.com", password="Str0ng!pass", full_name="L")

    def test_login_ok(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "Str0ng!pass"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data); self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "l@example.com")

    def test_login_bad_creds_401(self):
        resp = self.client.post("/api/v1/auth/login/", {"email": "l@example.com", "password": "nope"}, format="json")
        self.assertEqual(resp.status_code, 401)
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3 (impl):** `MeSerializer` in serializers.py:
```python
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "is_email_verified")
        read_only_fields = ("id", "email", "is_email_verified")
```
Login view (extends simplejwt to add user + throttle):
```python
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
```
(`MeSerializer` must be imported in views.py.) Add url `path("login/", views.LoginView.as_view(), name="login")`. NOTE: simplejwt's `TokenObtainPairSerializer` already uses `USERNAME_FIELD` (email) since our User sets it; `username_field = "email"` makes the request field `email`.
- [ ] **Step 4:** PASS.  **Step 5:** commit `feat(accounts): login endpoint returning tokens + user`.

## Task 5: Logout (TDD — blacklist)
**Files:** `views.py`, `urls.py`, `tests_auth.py`
- [ ] **Step 1 (red):** authenticated logout with a refresh token → 205; the refresh is then unusable at `token/refresh/` (→ 401).
```python
class LogoutTests(APITestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="o@example.com", password="Str0ng!pass")
        r = self.client.post("/api/v1/auth/login/", {"email": "o@example.com", "password": "Str0ng!pass"}, format="json")
        self.access, self.refresh = r.data["access"], r.data["refresh"]

    def test_logout_blacklists_refresh(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.post("/api/v1/auth/logout/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, 205)
        self.client.credentials()
        again = self.client.post("/api/v1/auth/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(again.status_code, 401)
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3 (impl):**
```python
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except (KeyError, TokenError):
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)
```
url `path("logout/", views.LogoutView.as_view(), name="logout")`.
- [ ] **Step 4:** PASS.  **Step 5:** commit `feat(accounts): logout endpoint (refresh blacklist)`.

## Task 6: Password reset request + confirm (TDD, no enumeration)
**Files:** `serializers.py`, `views.py`, `urls.py`, `tests_auth.py`
- [ ] **Step 1 (red):**
```python
class PasswordResetTests(APITestCase):
    def test_request_sends_email_for_existing_user(self):
        User.objects.create_user(email="p@example.com", password="Str0ng!pass")
        resp = self.client.post("/api/v1/auth/password-reset/", {"email": "p@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200); self.assertEqual(len(mail.outbox), 1)

    def test_request_unknown_email_still_200_no_email(self):
        resp = self.client.post("/api/v1/auth/password-reset/", {"email": "nobody@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200); self.assertEqual(len(mail.outbox), 0)

    def test_confirm_sets_new_password(self):
        from accounts.tokens import make_uid_token
        u = User.objects.create_user(email="c@example.com", password="OldPass!123")
        uid, token = make_uid_token(u)
        resp = self.client.post("/api/v1/auth/password-reset-confirm/",
            {"uid": uid, "token": token, "new_password": "Brand!New9"}, format="json")
        self.assertEqual(resp.status_code, 200)
        u.refresh_from_db(); self.assertTrue(u.check_password("Brand!New9"))
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3 (impl):** views:
```python
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .emails import send_password_reset_email


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = request.data.get("email", "")
        user = User.objects.filter(email__iexact=email).first()
        if user:
            send_password_reset_email(user)
        return Response({"detail": "If that email exists, a reset link was sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = read_uid_token(request.data.get("uid"), request.data.get("token"))
        new_password = request.data.get("new_password", "")
        if user is None:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, user)
        except DjangoValidationError as e:
            return Response({"new_password": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password); user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})
```
(`User` import already in views; ensure imports.) urls:
```python
path("password-reset/", views.PasswordResetView.as_view(), name="password-reset"),
path("password-reset-confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
```
- [ ] **Step 4:** PASS.  **Step 5:** commit `feat(accounts): password reset request + confirm`.

## Task 7: Profile me/ (TDD)
**Files:** `views.py`, `urls.py`, `tests_auth.py`
- [ ] **Step 1 (red):** authed GET returns the user; PATCH updates full_name; unauthed → 401.
```python
class MeTests(APITestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="m@example.com", password="Str0ng!pass", full_name="Me")
        r = self.client.post("/api/v1/auth/login/", {"email": "m@example.com", "password": "Str0ng!pass"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_get_me(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, 200); self.assertEqual(resp.data["email"], "m@example.com")

    def test_patch_full_name(self):
        resp = self.client.patch("/api/v1/auth/me/", {"full_name": "Renamed"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.u.refresh_from_db(); self.assertEqual(self.u.full_name, "Renamed")

    def test_me_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3 (impl):**
```python
class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
```
url `path("me/", views.MeView.as_view(), name="me")`.
- [ ] **Step 4:** PASS.  **Step 5:** Run the FULL backend suite (`manage.py test`) — expect all green. commit `feat(accounts): profile me endpoint`.

## Task 8: Frontend auth context + protected route + api
**Files:** `frontend/src/auth/AuthContext.jsx`, `frontend/src/auth/ProtectedRoute.jsx`, edits to `frontend/src/api/client.js`
- [ ] **Step 1:** Add auth API helpers to `client.js` (append):
```javascript
export const authApi = {
  register: (d) => api.post("/auth/register/", d),
  verifyEmail: (d) => api.post("/auth/verify-email/", d),
  login: (d) => api.post("/auth/login/", d),
  logout: (refresh) => api.post("/auth/logout/", { refresh }),
  passwordReset: (email) => api.post("/auth/password-reset/", { email }),
  passwordResetConfirm: (d) => api.post("/auth/password-reset-confirm/", d),
  me: () => api.get("/auth/me/"),
  updateMe: (d) => api.patch("/auth/me/", d),
}
```
- [ ] **Step 2:** `AuthContext.jsx`:
```jsx
import { createContext, useContext, useEffect, useState } from "react"
import { authApi } from "@/api/client"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (localStorage.getItem("access")) {
      authApi.me().then((r) => setUser(r.data)).catch(() => {}).finally(() => setLoading(false))
    } else setLoading(false)
  }, [])

  async function login(email, password) {
    const { data } = await authApi.login({ email, password })
    localStorage.setItem("access", data.access)
    localStorage.setItem("refresh", data.refresh)
    setUser(data.user)
  }

  async function logout() {
    const refresh = localStorage.getItem("refresh")
    try { if (refresh) await authApi.logout(refresh) } catch { /* ignore */ }
    localStorage.removeItem("access"); localStorage.removeItem("refresh"); setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```
- [ ] **Step 3:** `ProtectedRoute.jsx`:
```jsx
import { Navigate } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}
```
- [ ] **Step 4:** Wrap `<App/>` in `<AuthProvider>` in `main.jsx` (inside `<BrowserRouter>`). `npm run build` clean.
- [ ] **Step 5:** commit `feat(accounts): frontend auth context + protected route + api helpers`.

## Task 9: Frontend auth screens + routes
**Files:** `frontend/src/routes/{Register,Login,VerifyEmail,ForgotPassword,ResetPassword,Profile}.jsx`, edits to `App.jsx`
Build six screens using shadcn primitives (`Input`, `Label`, `Button`, `Card` if added, `toast` from sonner). Each is a small controlled form calling `authApi`. Requirements:
- **Login:** email+password → `useAuth().login()` → navigate `/profile`; show error toast on 401.
- **Register:** email+password+full_name → `authApi.register` → success toast "Check your email to verify" → navigate `/login`.
- **VerifyEmail:** reads `uid`/`token` from `useSearchParams()`, POSTs `authApi.verifyEmail` on mount, shows success/failure.
- **ForgotPassword:** email → `authApi.passwordReset` → always show "If that email exists…".
- **ResetPassword:** reads `uid`/`token` from query, new-password field → `authApi.passwordResetConfirm` → navigate `/login`.
- **Profile (protected):** shows `user.email`, editable `full_name` (PATCH via `authApi.updateMe`), a verify-status badge, and a Logout button (`useAuth().logout()` → navigate `/login`).
Wire routes in `App.jsx`: public `/login /register /verify-email /forgot-password /reset-password`; protected `/profile` (wrap in `<ProtectedRoute>`); update nav to show Login/Register when logged out and Profile/Logout when logged in (via `useAuth()`).
- [ ] Build each, `npm run build` clean, then commit `feat(accounts): auth screens (register/login/verify/reset/profile)`.

## Task 10: Phase 1 wrap-up
- [ ] Run full backend suite (all auth + Phase 0 tests green) + `manage.py check` + `npm run build`.
- [ ] Update `memory/current-state.md` (Phase 1 done; next Phase 2) + `progress-log.md`; `MEMORY.md` status line.
- [ ] Commit; the phase-1 branch is ready to merge into `main`.

## Self-review
- Spec coverage: signup ✓(T2) verify ✓(T3) login ✓(T4) logout ✓(T5) reset ✓(T6) profile ✓(T7) security: Argon2 (Phase 0) + JWT + scoped throttles ✓(T1,T4) + AllowAny discipline ✓(D7). Frontend ✓(T8-9).
- No placeholders; every backend step has real code/tests. Frontend screens specified by contract + the shared AuthContext/api are fully coded.
- Consistency: `read_uid_token`/`make_uid_token`, `MeSerializer`, `authApi`, endpoint slugs all consistent across tasks.
