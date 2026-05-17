import { useState, useEffect } from "react";
import {
  Database, Shield, Zap, Clock, CheckCircle2,
  ChevronRight, X, LayoutDashboard
} from "lucide-react";
import Logo from "../components/Logo";

interface Feature {
  id: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  list: string[];
  details: string;
}

const featuresData: Feature[] = [
  {
    id: 1,
    icon: <Shield className="w-6 h-6" />,
    title: "Secure Authentication",
    description: "OAuth 2.0 protected login ensures your Google account credentials are never stored on our servers.",
    list: ["Zero password storage", "Encrypted connections", "RA 10173 compliant"],
    details: "We utilize the official Google Identity Services SDK to handle the OAuth 2.0 Authorization Code Flow. This means your password never touches our backend. We only receive a temporary access token which is encrypted using AES-256 before being stored in a secure HTTP-only cookie."
  },
  {
    id: 2,
    icon: <Database className="w-6 h-6" />,
    title: "AI-Powered Organization",
    description: "Our Machine Learning engine automatically analyzes and sorts your files into smart categories.",
    list: ["Auto-categorization", "Separates School vs. Personal", "Smart tagging system"],
    details: "This is the core intelligence of DriveSafe. Using Python's 'scikit-learn' library, our backend analyzes file metadata (extensions, naming patterns, and sizes). It runs a classification algorithm to tag files as 'Academic', 'Multimedia', or 'Personal' before zipping them."
  },
  {
    id: 3,
    icon: <Zap className="w-6 h-6" />,
    title: "One-Click Backup",
    description: "Start a complete backup with a single click. Our system automatically fetches, compresses, and secures files.",
    list: ["Automated file fetching", "Smart ZIP compression", "Process in under 2 minutes"],
    details: "Our Python backend uses the Google Drive API v3 to recursively walk through your folders. It streams file data directly into a ZIP archive using the 'zipfile' library, meaning we don't need to save temporary files to our disk."
  },
  {
    id: 4,
    icon: <CheckCircle2 className="w-6 h-6" />,
    title: "Data Integrity",
    description: "Every backup includes MD5 checksum verification to ensure your files are perfectly preserved.",
    list: ["MD5 checksum generation", "Integrity verification", "Corruption detection"],
    details: "After creating the ZIP archive, we calculate its MD5 hash and compare it against the checksums provided by Google Drive's metadata. If even a single bit is different, the system flags the backup as 'Corrupted'."
  },
  {
    id: 5,
    icon: <Clock className="w-6 h-6" />,
    title: "Backup History",
    description: "Access and manage your last 5 backups. View detailed metadata including file count and size.",
    list: ["Last 5 backups tracked", "Detailed metadata display", "Easy download access"],
    details: "We use a lightweight SQLite database to track your backup history. Each entry stores the timestamp, file size, file count, and expiration date."
  },
  {
    id: 6,
    icon: <LayoutDashboard className="w-6 h-6" />,
    title: "Smart Archiving",
    description: "Archives are stored securely for 7 days, giving you time to download while managing storage.",
    list: ["7-day secure storage", "Auto-deletion policy", "Expiration tracking"],
    details: "A scheduled 'Cron Job' runs on our server every midnight. It checks the creation date of all ZIP files. Any file older than 7 days is securely wiped using a secure delete standard."
  }
];

const FeaturesPage = () => {
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);

  useEffect(() => {
    document.body.style.overflow = selectedFeature ? 'hidden' : 'unset';
    return () => { document.body.style.overflow = 'unset'; };
  }, [selectedFeature]);

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
            <h1 className="text-4xl md:text-5xl font-black text-gray-900 tracking-tight uppercase">Powerful Features</h1>
            <p className="text-xl text-gray-500 font-medium">Everything you need for institutional archival integrity</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {featuresData.map((f) => (
                <div 
                    key={f.id} 
                    onClick={() => setSelectedFeature(f)}
                    className="bg-white p-8 rounded-3xl border border-gray-100 shadow-sm hover:shadow-xl hover:border-indigo-100 transition-all cursor-pointer group"
                >
                    <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600 mb-6 group-hover:bg-indigo-600 group-hover:text-white transition-all shadow-inner">
                        {f.icon}
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-3 uppercase tracking-tight">{f.title}</h3>
                    <p className="text-gray-500 text-sm leading-relaxed mb-6">{f.description}</p>
                    <ul className="space-y-2 mb-6">
                        {f.list.map((item, i) => (
                            <li key={i} className="flex items-center gap-2 text-xs font-bold text-gray-400">
                                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> {item}
                            </li>
                        ))}
                    </ul>
                    <div className="flex items-center gap-2 text-indigo-600 text-xs font-black uppercase tracking-widest">
                        Learn more <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                </div>
            ))}
        </div>
      </main>

      {selectedFeature && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-gray-900/40 backdrop-blur-sm animate-in fade-in duration-300" onClick={() => setSelectedFeature(null)}>
              <div className="bg-white w-full max-w-2xl rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300 transition-all" onClick={e => e.stopPropagation()}>
                  <div className="p-8 md:p-12 space-y-8">
                      <div className="flex items-start justify-between">
                          <div className="flex items-center gap-4">
                              <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-100">
                                  {selectedFeature.icon}
                              </div>
                              <div>
                                  <h2 className="text-2xl font-black text-gray-900 tracking-tight uppercase">{selectedFeature.title}</h2>
                                  <p className="text-indigo-600 font-bold text-xs uppercase tracking-widest">Technical Deep Dive</p>
                              </div>
                          </div>
                          <button onClick={() => setSelectedFeature(null)} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-full transition-all">
                              <X className="w-6 h-6" />
                          </button>
                      </div>

                      <div className="space-y-6">
                          <div className="space-y-2">
                              <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Description</h4>
                              <p className="text-gray-600 leading-relaxed font-medium">{selectedFeature.description}</p>
                          </div>
                          <div className="space-y-2">
                              <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Mechanism</h4>
                              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-100 text-sm text-gray-600 leading-relaxed font-medium italic">
                                  "{selectedFeature.details}"
                              </div>
                          </div>
                      </div>

                      <button 
                        onClick={() => setSelectedFeature(null)}
                        className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold uppercase tracking-widest shadow-lg shadow-indigo-100 transition-all"
                      >
                        Close Details
                      </button>
                  </div>
              </div>
          </div>
      )}

      <footer className="p-10 text-center text-[10px] font-black text-gray-400 uppercase tracking-widest border-t border-gray-100 bg-white transition-colors">
        &copy; 2026 DriveSafe Features &bull; Optimized for Excellence
      </footer>
    </div>
  );
};

export default FeaturesPage;
