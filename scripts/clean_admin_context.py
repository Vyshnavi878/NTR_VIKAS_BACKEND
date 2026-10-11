import os
import re

admin_context_path = r"c:\Users\DELL\Downloads\ntrvikas\NTR_Vikasa_Frontend\src\context\AdminContext.jsx"

with open(admin_context_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the large block from '// ─── 2. SEED PLATFORM CANDIDATES / STUDENTS' to right before '// ─── 12. SEED SYSTEM SETTINGS'
pattern = r"// ─── 2\. SEED PLATFORM CANDIDATES / STUDENTS.*?(?=// ─── 12\. SEED SYSTEM SETTINGS)"
replacement = """// ─── 2. PLATFORM DATASETS (EMPTY INITIAL LIVE STATE) ───────────────────────
export const SEED_CANDIDATES = [];
const SEED_RECRUITERS = [];
const SEED_COMPANIES = [];
const SEED_JOBS = [];
const SEED_INTERNSHIPS = [];
const SEED_APPLICATIONS = [];
const SEED_JOB_MELAS = [];
const SEED_REGISTRATIONS = [];
const SEED_REPORTS = [];
const SEED_AUDIT_LOGS = [];
const SEED_NOTIFICATIONS = [];

"""

new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
print(f"Seed replacement matches: {count}")
if count != 1:
    raise ValueError(f"Expected 1 match for seed replacement, got {count}")

# 2. Update DEFAULT_HOME_CONTENT stats
new_content = re.sub(
    r"stats:\s*\[\s*\{\s*id:\s*'stat-1',\s*label:\s*'Active Jobs',\s*value:\s*'[^']+',\s*icon:\s*'Briefcase'\s*\},\s*\{\s*id:\s*'stat-2',\s*label:\s*'Verified Companies',\s*value:\s*'[^']+',\s*icon:\s*'Building2'\s*\},\s*\{\s*id:\s*'stat-3',\s*label:\s*'Registered Candidates',\s*value:\s*'[^']+',\s*icon:\s*'Users'\s*\},\s*\{\s*id:\s*'stat-4',\s*label:\s*'Successful Placements',\s*value:\s*'[^']+',\s*icon:\s*'TrendingUp'\s*\},\s*\]",
    """stats: [
    { id: 'stat-1', label: 'Active Jobs', value: '0', icon: 'Briefcase' },
    { id: 'stat-2', label: 'Verified Companies', value: '0', icon: 'Building2' },
    { id: 'stat-3', label: 'Registered Candidates', value: '0', icon: 'Users' },
    { id: 'stat-4', label: 'Successful Placements', value: '0', icon: 'TrendingUp' },
  ]""",
    new_content
)

# 3. Update DEFAULT_ABOUT_CONTENT stats
new_content = re.sub(
    r"stats:\s*\[\s*\{\s*id:\s*'ab-stat-1',\s*label:\s*'Registered Job Seekers',\s*value:\s*'[^']+',\s*color:\s*'[^']+'\s*\},\s*\{\s*id:\s*'ab-stat-2',\s*label:\s*'Confirmed Placements',\s*value:\s*'[^']+',\s*color:\s*'[^']+'\s*\},\s*\{\s*id:\s*'ab-stat-3',\s*label:\s*'Verified Hiring Employers',\s*value:\s*'[^']+',\s*color:\s*'[^']+'\s*\},\s*\{\s*id:\s*'ab-stat-4',\s*label:\s*'State-Wide Job Melas Held',\s*value:\s*'[^']+',\s*color:\s*'[^']+'\s*\},\s*\]",
    """stats: [
    { id: 'ab-stat-1', label: 'Registered Job Seekers', value: '0', color: 'var(--color-primary-600)' },
    { id: 'ab-stat-2', label: 'Confirmed Placements', value: '0', color: 'var(--color-success-600)' },
    { id: 'ab-stat-3', label: 'Verified Hiring Employers', value: '0', color: 'var(--color-warning-600)' },
    { id: 'ab-stat-4', label: 'State-Wide Job Melas Held', value: '0', color: 'var(--color-info-600)' },
  ]""",
    new_content
)

# 4. Insert localStorage eviction hook right inside AdminProvider
eviction_hook = """  // Evict legacy cached mock/seed records from localStorage
  useEffect(() => {
    const isLegacyDummy = (item) => {
      if (!item) return false;
      const id = String(item.id || item.mela_id || '');
      if (/^(cand-\\d+|rec-\\d+|comp-\\d+|job-\\d+|int-\\d+|app-\\d+|mela-\\d+|reg-\\d+|rep-\\d+|aud-\\d+|notif-\\d+)$/i.test(id)) return true;
      if (item.email && /@(example\\.com|techsolutionsglobal\\.com|amaravaticyber\\.com|fastcashenterprises\\.com)/i.test(item.email)) return true;
      if (item.company && /(Tech Solutions Global|NextGen Autonomous|Amaravati Cyber|Fast Cash Enterprises|ABC Technologies)/i.test(item.company)) return true;
      if (item.company_name && /(Tech Solutions Global|NextGen Autonomous|Amaravati Cyber|Fast Cash Enterprises|ABC Technologies)/i.test(item.company_name)) return true;
      if (item.title && /(Bengaluru Mega IT|AP Mega IT|Vijayawada Capital Region|Tirupati Rayalaseema|Guntur & Amaravati|Hyderabad Cyberabad)/i.test(item.title)) return true;
      return false;
    };

    [
      'ntr_admin_candidates_v1',
      'ntr_admin_recruiters_v1',
      'ntr_admin_companies_v1',
      'ntr_admin_jobs_v1',
      'ntr_admin_internships_v1',
      'ntr_admin_applications_v1',
      'ntr_admin_job_melas_v1',
      'ntr_admin_registrations_v1',
      'ntr_admin_reports_v1',
      'ntr_admin_audit_logs_v1',
      'ntr_admin_notifications_v1',
    ].forEach((key) => {
      try {
        const raw = localStorage.getItem(key);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.some(isLegacyDummy)) {
            localStorage.removeItem(key);
          }
        }
      } catch (e) {
        // ignore
      }
    });
  }, []);
"""

# Place it right after `export function AdminProvider({ children }) {`
new_content = new_content.replace(
    "export function AdminProvider({ children }) {\n",
    "export function AdminProvider({ children }) {\n" + eviction_hook + "\n",
    1
)

with open(admin_context_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Successfully updated AdminContext.jsx! New length: {len(new_content)} chars")
