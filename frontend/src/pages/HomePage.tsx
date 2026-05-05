import { 
  Shield, 
  Zap, 
  Clock, 
  ArrowRight, 
  CheckCircle2
} from 'lucide-react';
import Logo from '../components/Logo';

const HomePage = () => {
  const handleGetStarted = () => {
    window.location.hash = "signin";
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans relative overflow-hidden transition-colors duration-300">
      {/* Background Mesh Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-500/10 blur-[100px] pointer-events-none"></div>

      {/* Navigation (Glassmorphism) */}
      <nav className="bg-white/70 backdrop-blur-lg border-b border-gray-200/50 sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo size={50} />
            <span className="text-xl font-black text-gray-900 tracking-tight ml-1 uppercase">DriveSafe</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-bold text-gray-500 uppercase tracking-widest">
            <a href="#" className="hover:text-indigo-600 transition-colors">Home</a>
            <a href="#features" className="hover:text-indigo-600 transition-colors">Features</a>
            <a href="#about" className="hover:text-indigo-600 transition-colors">About</a>
            <button 
              onClick={handleGetStarted}
              className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-black hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 relative z-10">
        <section className="py-24 px-6 relative">
          <div className="max-w-7xl mx-auto text-center space-y-8">
            <div className="inline-flex items-center gap-2 bg-white/60 backdrop-blur-sm border border-indigo-100 px-5 py-2 rounded-full text-indigo-700 text-xs font-black uppercase tracking-widest shadow-sm">
              <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
              Free for Students & Educators
            </div>
            <h1 className="text-5xl md:text-7xl font-black text-gray-900 tracking-tighter max-w-4xl mx-auto leading-[1.1] uppercase">
              Automated Google Drive <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 animate-pulse">Backup Tool</span>
            </h1>
            <p className="text-xl text-gray-500 font-medium max-w-2xl mx-auto leading-relaxed">
              Protect your academic files with one-click automated backups. Simple, secure, and compliant with data privacy laws.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
              <button 
                onClick={handleGetStarted}
                className="w-full sm:w-auto bg-indigo-600 text-white px-8 py-4 rounded-2xl font-black text-sm uppercase tracking-widest hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-200 hover:shadow-2xl hover:-translate-y-1 flex items-center justify-center gap-3"
              >
                Get Started Free <ArrowRight className="w-5 h-5" />
              </button>
              <a 
                href="#features"
                className="w-full sm:w-auto bg-white border border-gray-200 text-gray-700 px-8 py-4 rounded-2xl font-black text-sm uppercase tracking-widest hover:bg-gray-50 hover:border-gray-300 transition-all text-center shadow-sm hover:shadow-md"
              >
                View Features
              </a>
            </div>
            
            <div className="pt-12 flex flex-wrap justify-center gap-8 text-xs font-bold text-gray-400 uppercase tracking-widest">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> No credit card required
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> RA 10173 compliant
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> MD5 verified
              </div>
            </div>
          </div>
        </section>

        {/* Features Preview */}
        <section id="features" className="py-24 bg-white/50 backdrop-blur-3xl border-y border-gray-200/50">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="p-8 rounded-[2.5rem] bg-white border border-gray-100 shadow-sm hover:shadow-2xl hover:border-indigo-100 hover:-translate-y-2 transition-all duration-500 group">
                <div className="w-14 h-14 bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-2xl flex items-center justify-center text-indigo-600 mb-6 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300 shadow-inner">
                  <Shield className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-3 uppercase tracking-tight">Enterprise Security</h3>
                <p className="text-gray-500 font-medium leading-relaxed">
                  OAuth 2.0 authentication ensures your data remains private and secure under your control.
                </p>
              </div>

              <div className="p-8 rounded-[2.5rem] bg-white border border-gray-100 shadow-sm hover:shadow-2xl hover:border-purple-100 hover:-translate-y-2 transition-all duration-500 group">
                <div className="w-14 h-14 bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl flex items-center justify-center text-purple-600 mb-6 group-hover:scale-110 group-hover:-rotate-3 transition-transform duration-300 shadow-inner">
                  <Zap className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-3 uppercase tracking-tight">Lightning Fast</h3>
                <p className="text-gray-500 font-medium leading-relaxed">
                  Process up to 100 files in under 2 minutes with our optimized multi-threaded engine.
                </p>
              </div>

              <div className="p-8 rounded-[2.5rem] bg-white border border-gray-100 shadow-sm hover:shadow-2xl hover:border-pink-100 hover:-translate-y-2 transition-all duration-500 group">
                <div className="w-14 h-14 bg-gradient-to-br from-pink-50 to-pink-100 rounded-2xl flex items-center justify-center text-pink-600 mb-6 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300 shadow-inner">
                  <Clock className="w-7 h-7 animate-float" />
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-3 uppercase tracking-tight">Backup History</h3>
                <p className="text-gray-500 font-medium leading-relaxed">
                  Access and manage your version history easily with our intuitive ledger system.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Trusted By */}
        <section className="py-24 px-6">
          <div className="max-w-7xl mx-auto text-center space-y-10">
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">Trusted by students and educators at</p>
            <div className="flex justify-center">
              <div className="bg-white/80 backdrop-blur-md px-10 py-5 rounded-2xl border border-gray-200/50 shadow-lg shadow-gray-200/20 text-gray-800 font-black tracking-tighter text-2xl md:text-3xl hover:scale-105 transition-transform duration-500 cursor-default">
                CEBU INSTITUTE OF TECHNOLOGY UNIVERSITY
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white/80 backdrop-blur-md border-t border-gray-200/50 py-12 px-6 text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] text-center z-10 transition-colors">
        <p>&copy; 2026 DriveSafe &bull; RA 10173 Compliant &bull; Secure Archival System</p>
      </footer>
    </div>
  );
};

export default HomePage;
