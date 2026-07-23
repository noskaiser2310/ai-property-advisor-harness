"""
Dynamic Skill Loader — Loads domain skill packages into prompt context on demand
"""
import os
import glob
import logging
from typing import Dict, List

log = logging.getLogger("ai-property-advisor.harness.skills")

SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "skills"))


class SkillLoader:
    """Dynamically loads markdown skill instructions based on query topic"""

    _cache: Dict[str, str] = {}

    @classmethod
    def load_all_skills(cls) -> Dict[str, str]:
        """Scan skills directory and load all SKILL.md files"""
        if cls._cache:
            return cls._cache

        skills = {}
        pattern = os.path.join(SKILLS_DIR, "**", "SKILL.md")
        for filepath in glob.glob(pattern, recursive=True):
            skill_name = os.path.basename(os.path.dirname(filepath))
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    skills[skill_name] = content
            except Exception as e:
                log.warning("Failed to load skill %s: %s", skill_name, e)

        cls._cache = skills
        log.info("Loaded %d skill packages: %s", len(skills), list(skills.keys()))
        return skills

    @classmethod
    def select_relevant_skills(cls, question: str) -> str:
        """Select skills matching question keywords to avoid polluting system prompt"""
        all_skills = cls.load_all_skills()
        selected_texts = []

        q_lower = question.lower()

        # Keywords mapping — expanded for better semantic coverage
        if any(k in q_lower for k in ["báo cáo", "tài chính", "doanh thu", "chi phí", "lợi nhuận", "nợ", "công nợ", "sức khỏe", "dòng tiền", "tỉ suất", "biên lợi", "tăng trưởng", "thất thoát", "lãi", "lỗ", "thu nhập"]):
            if "financial_analysis" in all_skills:
                selected_texts.append(f"--- SKILL: financial_analysis ---\n{all_skills['financial_analysis']}")

        if any(k in q_lower for k in ["bài đăng", "tìm khách", "cho thuê", "viết bài", "phòng trống", "tiện ích", "quảng cáo", "marketing", "đăng tin", "facebook", "zalo", "chợ tốt"]):
            if "marketing_copywriting" in all_skills:
                selected_texts.append(f"--- SKILL: marketing_copywriting ---\n{all_skills['marketing_copywriting']}")

        if any(k in q_lower for k in ["danh sách", "tra cứu", "sql", "phòng", "hóa đơn", "hợp đồng", "bảo trì", "trạng thái", "chi tiết", "mã phòng", "chỉ số", "điện nước", "khách thuê", "người thuê", "liệt kê", "thống kê", "số liệu"]):
            if "sql_best_practices" in all_skills:
                selected_texts.append(f"--- SKILL: sql_best_practices ---\n{all_skills['sql_best_practices']}")

        if not selected_texts and "financial_analysis" in all_skills:
            selected_texts.append(f"--- SKILL: financial_analysis ---\n{all_skills['financial_analysis']}")

        return "\n\n".join(selected_texts)
