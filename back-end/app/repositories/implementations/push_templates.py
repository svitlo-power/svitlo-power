from shared.models.push_template import PushTemplate
from ..interfaces.push_templates import IPushTemplatesRepository


class PushTemplatesRepository(IPushTemplatesRepository):

    async def get_all_templates(self) -> list[PushTemplate]:
        return await PushTemplate.find_all().to_list()

    async def get_template(self, topic: str) -> PushTemplate | None:
        return await PushTemplate.find_one(PushTemplate.topic == topic)

    async def add_template(self, template: PushTemplate) -> PushTemplate:
        await template.insert()
        return template

    async def save_template(self, template: PushTemplate) -> PushTemplate:
        await template.save()
        return template
