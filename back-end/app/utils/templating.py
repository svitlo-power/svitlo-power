from jinja2 import Environment


def _create_environment():
    return Environment(
        lstrip_blocks=True,
        trim_blocks=True,
        enable_async=True,
    )


async def _create_template(
    template: str,
    template_macros: str | None = None,
):
    environment = _create_environment()

    if template_macros:
        macro_template = environment.from_string(template_macros)
        macro_module = await macro_template.make_module_async()

        for name in dir(macro_module):
            if not name.startswith("_"):
                environment.globals[name] = getattr(macro_module, name)

    return environment.from_string(template)


async def generate_message(
    template_str: str,
    data: dict,
    template_macros: str | None = None,
):
    try:
        template = await _create_template(template_str, template_macros)
        return await template.render_async(data)
    except Exception as e:
        raise Exception(f"Error in 'Message' template: {repr(e)}")


async def get_send_timeout(
    template_str: str,
    data: dict,
    template_macros: str | None = None,
) -> int:
    try:
        template = await _create_template(template_str, template_macros)
        return int(await template.render_async(data))
    except Exception as e:
        raise Exception(f"Error in 'Send timeout' template: {repr(e)}")


async def get_should_send(
    template_str: str,
    data: dict,
    template_macros: str | None = None,
) -> bool:
    if template_str is None:
        return True

    try:
        template = await _create_template(template_str, template_macros)
        result = await template.render_async(data)
        return result is not None and result.lower().capitalize() == "True"
    except Exception as e:
        raise Exception(f"Error in 'Should send' template: {repr(e)}")
