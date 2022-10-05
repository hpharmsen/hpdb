import sys


def bump(file, tag, what='minor', new_version=None):
    with open(file, 'r') as f:
        lines = f.readlines()
        for index, line in enumerate(lines):
            if line.startswith(tag):
                version = line.removeprefix(tag).strip()
                quoted = version[0] == '"'
                if not new_version:
                    if quoted:
                        version = version.strip('"')
                    major, minor, patch = version.split('.')
                    if what == 'major':
                        major = int(major) + 1
                        minor = 0
                        patch = 0
                    elif what == 'minor':
                        minor = int(minor) + 1
                        patch = 0
                    else:
                        patch = int(patch) + 1
                    new_version = f"{major}.{minor}.{patch}"
                if quoted:
                    lines[index] = f'{tag}"{new_version}"\n'
                else:
                    lines[index] = f'{tag}{new_version}\n'
    with open(file, 'w') as f:
        f.writelines(lines)
    return new_version


if __name__ == "__main__":
    what = sys.argv[1]
    version = bump('pyproject.toml', "version = ", what=what)
    bump("README.md", "Current version: ", new_version=version)
    print('Updated version to', version)
