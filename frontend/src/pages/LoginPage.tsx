import { useGoogleLogin } from "@react-oauth/google";
import { ShieldCheck, X } from "lucide-react";
import Logo from "../components/Logo";

const LoginPage = () => {
  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: "openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets https://spreadsheets.google.com/feeds",
    // @ts-expect-error: prompt is required for consent but not in type
    prompt: 'consent', 
    onSuccess: async (codeResponse) => {
      try {
        const response = await fetch('/auth/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ code: codeResponse.code }),
        });
        const data = await response.json();
        if (response.ok) {
           localStorage.setItem('user_email', data.user_email);
           localStorage.setItem('user_name', data.user_name);
           window.location.hash = "dashboard";
        } else {
           alert("Login Failed: " + data.error);
        }
      } catch (error) {
        console.error("Login failed", error);
      }
    },
  });

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 font-sans transition-colors duration-300">
      {/* Branding top-left */}
      <div className="fixed top-0 left-0 p-6 flex items-center justify-between w-full">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.location.hash = ""}>
          <Logo size={50} />
          <span className="text-xl font-bold text-gray-900 tracking-tight uppercase">DriveSafe</span>
        </div>
      </div>

      <div className="w-full max-w-md bg-white rounded-[2.5rem] shadow-2xl border border-gray-100 overflow-hidden relative transition-all">
        <button 
          onClick={() => window.location.hash = ""}
          className="absolute top-8 right-8 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-full transition-all"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="p-10 md:p-12 text-center space-y-10">
          <div className="inline-flex items-center justify-center w-28 h-28 bg-indigo-50 rounded-[2rem] shadow-inner">
            <Logo size={90} />
          </div>
          
          <div className="space-y-3">
            <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Welcome Back</h1>
            <p className="text-gray-500 font-medium">Sign in to access your secure archives</p>
          </div>

          <button 
            onClick={() => googleLogin()}
            className="w-full flex items-center justify-center gap-4 py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-[1.5rem] font-black text-sm uppercase tracking-widest transition-all shadow-xl shadow-indigo-100 hover:shadow-2xl active:scale-[0.98] group"
          >
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Sign in with Google
          </button>

          <div className="pt-4 flex items-start gap-4 text-left bg-emerald-50 p-5 rounded-2xl border border-emerald-100">
            <ShieldCheck className="w-6 h-6 text-emerald-600 mt-0.5 shrink-0" />
            <p className="text-xs text-emerald-800 font-medium leading-relaxed uppercase tracking-tight">
              We're compliant with RA 10173 Data Privacy Act. Your data is encrypted and secure.
            </p>
          </div>
        </div>
        
        <div className="bg-gray-50 p-6 text-center border-t border-gray-100">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">
            Institutional Access Only &bull; Secure Protocol
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
