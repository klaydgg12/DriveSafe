import { ShieldCheck, Target, Users, Landmark, CheckCircle2 } from "lucide-react";
import Logo from "../components/Logo";

const AboutPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans transition-colors duration-300">
      <nav className="bg-white border-b border-gray-100 sticky top-0 z-50 transition-all">
        <div className="max-w-[1600px] mx-auto px-8 md:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.location.hash = ""}>
            <Logo size={40} />
            <span className="text-xl font-bold text-gray-900 tracking-tight uppercase">DriveSafe</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600 uppercase tracking-widest">
            <a href="#" className="hover:text-indigo-600 transition-colors">Home</a>
            <a href="#features" className="hover:text-indigo-600 transition-colors">Features</a>
            <a href="#about" className="hover:text-indigo-600 transition-colors">About</a>
            <button 
              onClick={() => window.location.hash = "signin"}
              className="bg-indigo-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-indigo-700 transition-all shadow-sm"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-[1600px] mx-auto w-full p-8 md:p-12 space-y-16">
        <div className="text-center space-y-4 pt-10">
            <div className="inline-flex items-center gap-2 bg-indigo-50 px-4 py-1.5 rounded-full text-indigo-700 text-xs font-black uppercase tracking-widest">
                Academic Project
            </div>
            <h1 className="text-4xl md:text-5xl font-black text-gray-900 tracking-tight uppercase">Excellence in Software Development</h1>
            <p className="text-xl text-gray-500 font-medium max-w-2xl mx-auto">
                DriveSafe is a capstone initiative by IT students of Cebu Institute of Technology University.
            </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="bg-white p-10 rounded-[2.5rem] border border-gray-100 shadow-sm space-y-6">
                <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-100">
                    <Target className="w-7 h-7" />
                </div>
                <h2 className="text-2xl font-black text-gray-900 tracking-tight uppercase">Project Objectives</h2>
                <p className="text-gray-500 font-medium leading-relaxed">
                    Addressing the critical need for automated backup solutions for educators who risk losing important academic files.
                </p>
                <div className="space-y-4 pt-4">
                    {[
                        { t: "Prevent Data Loss", d: "Protect files from account deactivation." },
                        { t: "Simplify Backups", d: "One-click solution for complex tasks." },
                        { t: "Ensure Compliance", d: "Full adherence to RA 10173." }
                    ].map((obj, i) => (
                        <div key={i} className="flex gap-4 p-4 bg-gray-50 rounded-2xl border border-gray-100">
                            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                            <div>
                                <h4 className="font-bold text-gray-900 text-sm uppercase tracking-tight">{obj.t}</h4>
                                <p className="text-xs text-gray-500 font-medium">{obj.d}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="bg-white p-10 rounded-[2.5rem] border border-gray-100 shadow-sm space-y-6">
                <div className="w-14 h-14 bg-amber-500 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-amber-100">
                    <ShieldCheck className="w-7 h-7" />
                </div>
                <h2 className="text-2xl font-black text-gray-900 tracking-tight uppercase">Problem Statement</h2>
                <p className="text-gray-500 font-medium leading-relaxed">
                    Account deactivation upon graduation leads to significant loss of academic assets accumulated over years.
                </p>
                <div className="p-6 bg-indigo-600 rounded-2xl text-white space-y-2 shadow-xl shadow-indigo-100">
                    <h3 className="font-black text-sm uppercase tracking-widest">Our Solution</h3>
                    <p className="text-sm font-medium leading-relaxed opacity-90">
                        DriveSafe automates the entire backup process with enterprise-grade security, ensuring institutional continuity.
                    </p>
                </div>
                <div className="p-6 bg-emerald-50 rounded-2xl border border-emerald-100 space-y-2">
                    <h3 className="text-emerald-700 font-black text-sm uppercase tracking-widest">The Challenge</h3>
                    <p className="text-sm text-emerald-800 font-medium leading-relaxed">
                        Providing a reliable, automated solution that maintains strict security and privacy compliance.
                    </p>
                </div>
            </div>
        </div>

        <div className="bg-white p-10 rounded-[3rem] border border-gray-100 shadow-sm space-y-10 transition-all">
            <div className="text-center space-y-2">
                <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-inner">
                    <Users className="w-7 h-7" />
                </div>
                <h2 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Development Team</h2>
                <p className="text-gray-500 font-bold text-xs uppercase tracking-widest">Information Technology • Class of 2025</p>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
                {[
                    "Lyrech James E. Laspiñas", "Louis Drey F. Castañeto", "John Earl F. Mandawe",
                    "Clyde Nixon Jumawan", "Mark Joenylle B. Cortes"
                ].map((name, i) => (
                    <div key={i} className="p-6 bg-gray-50 rounded-2xl text-center border border-gray-100 hover:border-indigo-100 transition-all group shadow-sm">
                        <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-4 text-indigo-600 font-black border border-gray-100 group-hover:bg-indigo-600 group-hover:text-white transition-all shadow-sm">
                            {name.charAt(0)}
                        </div>
                        <h4 className="text-xs font-black text-gray-900 leading-tight mb-1 uppercase tracking-tight">{name}</h4>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">Developer</p>
                    </div>
                ))}
            </div>
        </div>

        <div className="bg-indigo-900 rounded-[3rem] p-10 md:p-16 text-center text-white space-y-8 relative overflow-hidden shadow-2xl shadow-indigo-200">
            <div className="absolute top-0 left-0 w-full h-full opacity-5 pointer-events-none">
                <Landmark className="w-96 h-96 -ml-20 -mt-20 rotate-12" />
            </div>
            <div className="relative space-y-4">
                <h2 className="text-3xl font-black tracking-tight uppercase">Cebu Institute of Technology University</h2>
                <p className="text-indigo-200 font-bold text-sm uppercase tracking-[0.2em]">College of Computer Studies</p>
                <p className="max-w-3xl mx-auto text-lg font-medium opacity-80 leading-relaxed">
                    Committed to excellence in technology education, CIT-U empowers students to create innovative solutions that address real-world problems.
                </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative pt-8">
                {[
                    { l: "Version", v: "2.0 (2026)" },
                    { l: "Status", v: "Capstone Project" },
                    { l: "Institutional", v: "CIT-U / CCS" }
                ].map((item, i) => (
                    <div key={i} className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/10">
                        <h4 className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-1">{item.l}</h4>
                        <p className="text-xl font-black uppercase tracking-tight">{item.v}</p>
                    </div>
                ))}
            </div>
        </div>
      </main>

      <footer className="p-10 text-center text-[10px] font-black text-gray-400 uppercase tracking-widest border-t border-gray-100 bg-white transition-colors">
        &copy; 2026 DriveSafe &bull; Developed with Passion at CIT-U
      </footer>
    </div>
  );
};

export default AboutPage;
