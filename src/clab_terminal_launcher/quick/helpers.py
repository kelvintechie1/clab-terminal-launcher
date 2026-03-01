import click

def validate_required_keys(task: str, settings: dict[str, str | None], requiredKeys: dict[str, str], config: str) -> None:
    """Helper function to validate that all required keys are in a settings dictionary; error and exit if any key(s) is/are missing"""
    requiredKeysOnly = requiredKeys.values()
    keysPresent = [key in settings for key in requiredKeysOnly]
    if not all(keysPresent):
        print(f"Error while {task}, the following required keys are not present in {config}: {', '.join([requiredKeysOnly[i] for i, val in enumerate(keysPresent) if not val])}")
        exit(-1)

def parse_settings(settings: dict[str, str | None], searchKeys: dict[str, str]) -> dict[str, str]:
    """Helper function to process the settings dictionary in search of all of the keys in searchKeys
    and return a filtered dictionary with only those settings; skip any keys that aren't found in the
    original settings dictionary"""
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

def run_command(task: str, settings: dict[str, str | None], requiredKeys: dict[str, str], optionalKeys: dict[str, str],
         config: str, ctx: click.Context, func: click.Command) -> None:
    """Helper/runner function to, for a given task, validate that all required keys are present,
    parse all relevant/available settings, and run the relevant Click command given the Click context object"""
    validate_required_keys(task=f"validating {task} settings",
                           requiredKeys=requiredKeys,
                           settings=settings,
                           config=config)

    ctx.invoke(func, **parse_settings(settings=settings, searchKeys=(requiredKeys | optionalKeys)))