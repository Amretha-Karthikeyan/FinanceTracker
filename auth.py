"""
Authentication module — Supabase Auth with Streamlit session management.
Handles sign-up, sign-in, sign-out, and session persistence across reruns.
"""

import streamlit as st
from config import SUPABASE_URL, SUPABASE_KEY


def _get_auth_client():
    """Get a Supabase client for auth operations (uses anon key)."""
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_auth():
    """Initialize auth state in session. Call once at app start."""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None


def get_user():
    """Return the current authenticated user dict, or None."""
    return st.session_state.get("user")


def get_user_id() -> str | None:
    """Return the current user's UUID string, or None."""
    user = get_user()
    if user:
        return user.get("id") or user.get("sub")
    return None


def get_authenticated_client():
    """
    Return a Supabase client with the user's access token set,
    so that RLS policies work correctly.
    """
    from supabase import create_client

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")

    if access_token and refresh_token:
        try:
            sb.auth.set_session(access_token, refresh_token)
        except Exception:
            # Token expired — try refresh
            try:
                resp = sb.auth.refresh_session(refresh_token)
                if resp and resp.session:
                    st.session_state.access_token = resp.session.access_token
                    st.session_state.refresh_token = resp.session.refresh_token
                    sb.auth.set_session(resp.session.access_token, resp.session.refresh_token)
                else:
                    _clear_session()
                    return None
            except Exception:
                _clear_session()
                return None
    return sb


def sign_up(email: str, password: str) -> tuple[bool, str]:
    """
    Register a new user. Returns (success, message).
    """
    try:
        sb = _get_auth_client()
        resp = sb.auth.sign_up({"email": email, "password": password})

        if resp.user:
            # Some Supabase projects require email confirmation
            if resp.session:
                _store_session(resp)
                return True, "Account created and signed in!"
            else:
                return True, "Account created! Check your email to confirm, then sign in."
        return False, "Sign-up failed. Please try again."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already been registered" in msg.lower():
            return False, "This email is already registered. Please sign in."
        return False, f"Sign-up error: {msg}"


def sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in an existing user. Returns (success, message).
    """
    try:
        sb = _get_auth_client()
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})

        if resp.user and resp.session:
            _store_session(resp)
            return True, f"Welcome back, {email}!"
        return False, "Sign-in failed. Check your credentials."
    except Exception as e:
        msg = str(e)
        if "invalid" in msg.lower() or "credentials" in msg.lower():
            return False, "Invalid email or password."
        if "not confirmed" in msg.lower():
            return False, "Please confirm your email first (check your inbox)."
        return False, f"Sign-in error: {msg}"


def sign_out():
    """Sign out the current user."""
    try:
        sb = _get_auth_client()
        sb.auth.sign_out()
    except Exception:
        pass
    _clear_session()


def _store_session(resp):
    """Store auth response in Streamlit session state."""
    st.session_state.user = {
        "id": resp.user.id,
        "email": resp.user.email,
        "created_at": str(resp.user.created_at) if resp.user.created_at else None,
    }
    st.session_state.access_token = resp.session.access_token
    st.session_state.refresh_token = resp.session.refresh_token


def _clear_session():
    """Clear auth state."""
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None


def require_auth():
    """
    Auth gate — call at the top of your app.
    Shows login/signup if not authenticated, calls st.stop().
    Returns user dict if authenticated.
    """
    init_auth()

    if get_user():
        return get_user()

    # ── Show Login / Signup UI ────────────────────────────────
    st.set_page_config(
        page_title="Finance Tracker — Sign In",
        page_icon="💰",
        layout="centered",
    )

    st.markdown("""
    <style>
        .auth-header { text-align: center; margin-bottom: 30px; }
        .auth-header h1 { font-size: 2.5em; margin-bottom: 5px; }
        .auth-header p { color: #888; font-size: 1.1em; }
    </style>
    <div class="auth-header">
        <h1>💰 Finance Tracker</h1>
        <p>Track your spending, investments & savings</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔐 Sign In", "📝 Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    ok, msg = sign_in(email, password)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_pass")
            password2 = st.text_input("Confirm Password", type="password", key="signup_pass2")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif password != password2:
                    st.error("Passwords don't match.")
                else:
                    ok, msg = sign_up(email, password)
                    if ok:
                        st.success(msg)
                        if get_user():
                            st.rerun()
                    else:
                        st.error(msg)

    st.stop()
