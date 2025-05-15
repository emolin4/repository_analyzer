import requests
import json
from pathlib import Path
from collections import defaultdict

GITHUB_USER = "Biacuya" 
CONFIG_FILES = {
    "Python": ["requirements.txt", "pyproject.toml"],
    "JavaScript": ["package.json"],
    "Java": ["pom.xml"],
    "PHP": ["composer.json"]
}

EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", "coverage", ".next", "out"
}

headers = {
    "Authorization": ""
}


def get_repos(user: str):
    url = f"https://api.github.com/users/{user}/repos"
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else []

def get_default_branch(owner: str, repo: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("default_branch", "main")
    return "main"

def list_all_files_from_repo(owner: str, repo: str, branch: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        tree = res.json().get("tree", [])
        return [file["path"] for file in tree if file["type"] == "blob"]
    return []

def is_excluded(path: str) -> bool:
    return any(part in EXCLUDE_DIRS for part in Path(path).parts)

def detect_config_files(files: list[str]) -> dict[str, list[str]]:
    results = defaultdict(list)
    for file_path in files:
        if is_excluded(file_path):
            continue
        filename = Path(file_path).name
        for lang, candidates in CONFIG_FILES.items():
            if filename in candidates:
                results[lang].append(file_path)
    return results

def fetch_raw_file(owner: str, repo: str, branch: str, path: str):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    res = requests.get(url, headers=headers)
    return res.text if res.status_code == 200 else None

def parse_dependencies(content: str, config_file: str) -> dict:
    deps = {}
    try:
        if config_file == "package.json":
            data = json.loads(content)
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
        elif config_file == "requirements.txt":
            lines = content.splitlines()
            for line in lines:
                if "==" in line:
                    pkg, ver = line.split("==")
                    deps[pkg.strip()] = ver.strip()
                else:
                    deps[line.strip()] = "unknown"
        elif config_file == "pyproject.toml":
            import tomllib
            data = tomllib.loads(content.encode())
            deps.update(data.get("project", {}).get("dependencies", {}))
        elif config_file == "composer.json":
            data = json.loads(content)
            deps.update(data.get("require", {}))
    except Exception as e:
        print(f"Error parsing {config_file}: {e}")
    return deps


repos = get_repos(GITHUB_USER)

for repo in repos:
    repo_name = repo["name"]
    print(f"\nAnalizando repositorio: {repo_name}")
    branch = get_default_branch(GITHUB_USER, repo_name)
    files = list_all_files_from_repo(GITHUB_USER, repo_name, branch)

    config_files_by_lang = detect_config_files(files)
    if config_files_by_lang:
        for lang, paths in config_files_by_lang.items():
            print(f"Lenguaje detectado: {lang}")
            for config_file in paths:
                print(f"Archivo de configuración: {config_file}")
                raw = fetch_raw_file(GITHUB_USER, repo_name, branch, config_file)
                if raw:
                    deps = parse_dependencies(raw, Path(config_file).name)
                    if deps:
                        print("Dependencias encontradas:")
                        for k, v in deps.items():
                            print(f"  - {k}: {v}")
                    else:
                        print("No se detectaron dependencias.")
                else:
                    print("No se pudo obtener el contenido del archivo.")
    else:
        print("No se encontró ningún archivo de configuración reconocido.")
