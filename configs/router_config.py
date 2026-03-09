ROUTER_TABLE = {
    # ==========================================
    # 1. 架构导向任务 (Architecture-Oriented Tasks)
    # 信息源要求: README, module and package structure, entry point information
    # ==========================================
    "modular_structure": {
        "description": "Which repositories are organised into clearly separated modules or packages?",
        "mandatory_evidence": ["module_and_package_structure"],
        "optional_evidence": ["readme"]
    },
    "layered_design": {
        "description":
        "Which repositories show a layered structure (e.g., separation between core logic and interfaces)?",
        "mandatory_evidence": ["module_and_package_structure", "readme"],
        "optional_evidence": []
    },
    "library_vs_application": {
        "description": "Which repositories are designed as reusable libraries rather than standalone applications?",
        "mandatory_evidence": ["module_and_package_structure", "entry_points", "readme"],
        "optional_evidence": []
    },
    "script_based_projects": {
        "description": "Which repositories primarily consist of scripts rather than reusable modules?",
        "mandatory_evidence": ["module_and_package_structure", "entry_points"],
        "optional_evidence": []
    },

    # ==========================================
    # 2. 执行与使用任务 (Execution and Usage Tasks)
    # 信息源要求: 依赖架构信息（入口点）和文档
    # ==========================================
    "executable_entry_points": {
        "description": "Which repositories provide a clear entry point for execution (e.g., a main script or CLI)?",
        "mandatory_evidence": ["entry_points"],
        "optional_evidence": ["readme"]
    },
    "batch_vs_interactive": {
        "description": "Which repositories are designed to be executed in batch mode rather than interactively?",
        "mandatory_evidence": ["entry_points", "readme"],
        "optional_evidence": ["code_snippets"]  # 可能需要看入口函数里的循环或参数
    },
    "config_driven_execution": {
        "description": "Which repositories rely on configuration files or parameters to control execution?",
        "mandatory_evidence": ["entry_points", "readme"],
        "optional_evidence": ["imported_libraries"]  # 可能会导入 yaml, json, argparse 等
    },

    # ==========================================
    # 3. 实现聚焦任务 (Implementation-Focused Tasks)
    # 信息源要求: code snippets, docstrings, summaries of key functions/classes, 依赖列表
    # ==========================================
    "data_input_handling": {
        "description": "How does this repository read input data (e.g., files, configuration objects, parameters)?",
        "mandatory_evidence": ["code_snippets", "docstrings_summaries"],
        "optional_evidence": ["readme"]
    },
    "external_dependencies": {
        "description": "Which repositories rely heavily on external libraries or frameworks?",
        "mandatory_evidence": ["requirements_files", "imported_libraries"],
        "optional_evidence": []
    },
    "testing_support": {
        "description": "Which repositories include automated tests or testing infrastructure?",
        "mandatory_evidence": ["module_and_package_structure"],  # 找 tests/ 目录
        "optional_evidence": ["requirements_files"]  # 找 pytest 等依赖
    },
    "documentation_quality": {
        "description": "Which repositories provide structured documentation beyond a basic README?",
        "mandatory_evidence": ["readme", "docstrings_summaries"],
        "optional_evidence": []
    },

    # ==========================================
    # 4. 维护与复用导向任务 (Maintenance and Reuse-Oriented Tasks)
    # 信息源要求: 综合上述所有维度的信息
    # ==========================================
    "ease_of_reuse": {
        "description": "Which repositories appear easy to reuse or extend based on their structure and documentation?",
        "mandatory_evidence": ["module_and_package_structure", "readme", "docstrings_summaries"],
        "optional_evidence": []
    },
    "code_complexity_indicators": {
        "description":
        "Which repositories show signs of high structural complexity (e.g., deeply nested modules or large functions)?",
        "mandatory_evidence": ["module_and_package_structure", "code_snippets"],
        "optional_evidence": ["docstrings_summaries"]
    },
    "similarity_for_reuse": {
        "description":
        "Which repositories are most similar to a given repository in terms of structure and functionality?",
        "mandatory_evidence": ["module_and_package_structure", "readme", "entry_points"],
        "optional_evidence": ["imported_libraries"]
        # 注意：这个任务在主逻辑里需要标记 Requires Stage A = True
    },
    "functionality_location": {
        "description": "Where in the repository is the core functionality implemented?",
        "mandatory_evidence": ["module_and_package_structure", "docstrings_summaries"],
        "optional_evidence": ["entry_points"]
    }
}
