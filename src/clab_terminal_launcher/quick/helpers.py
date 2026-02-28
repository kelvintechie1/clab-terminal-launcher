def validate_required_keys(task: str, settings: dict[str, str | None], requiredKeys: dict[str, str], config: str) -> None:
    requiredKeysOnly = requiredKeys.values()
    keysPresent = [key in settings for key in requiredKeysOnly]
    if not all(keysPresent):
        print(f"Error while {task}, the following required keys are not present in {config}: {', '.join([requiredKeysOnly[i] for i, val in enumerate(keysPresent) if not val])}")
        exit(-1)

def parse_settings(settings: dict[str, str | None], searchKeys: dict[str, str]) -> dict[str, str]:
    parsedSettings = {}
    for key, value in searchKeys.items():
        try:
            settingValue = settings[value]
            if settingValue is not None:
                parsedSettings[key] = settingValue
        except KeyError:
            continue

    print(f"Found values for: {', '.join(parsedSettings)}")
    return parsedSettings