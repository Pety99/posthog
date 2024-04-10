# Generated by Django 3.2.5 on 2022-03-02 22:44
from typing import Any, List, Tuple

from django.core.paginator import Paginator
from django.db import migrations
from django.db.models import Q

from posthog.models.tag import tagify


def forwards(apps, schema_editor):
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("ee/0012_migrate_tags_v2_start")

    Tag = apps.get_model("posthog", "Tag")
    TaggedItem = apps.get_model("posthog", "TaggedItem")
    EnterpriseEventDefinition = apps.get_model("ee", "EnterpriseEventDefinition")
    EnterprisePropertyDefinition = apps.get_model("ee", "EnterprisePropertyDefinition")

    createables: List[Tuple[Any, Any]] = []
    batch_size = 1_000

    # Collect event definition tags and taggeditems
    event_definition_paginator = Paginator(
        EnterpriseEventDefinition.objects.exclude(
            Q(deprecated_tags__isnull=True) | Q(deprecated_tags=[]),
        )
        .order_by("created_at")
        .values_list("deprecated_tags", "team_id", "id"),
        batch_size,
    )

    for event_definition_page in event_definition_paginator.page_range:
        logger.info(
            "event_definition_tag_batch_get_start",
            limit=batch_size,
            offset=(event_definition_page - 1) * batch_size,
        )
        event_definitions = iter(event_definition_paginator.get_page(event_definition_page))
        for tags, team_id, event_definition_id in event_definitions:
            unique_tags = {tagify(t) for t in tags if isinstance(t, str) and t.strip() != ""}
            for tag in unique_tags:
                temp_tag = Tag(name=tag, team_id=team_id)
                createables.append(
                    (
                        temp_tag,
                        TaggedItem(event_definition_id=event_definition_id, tag_id=temp_tag.id),
                    )
                )

    logger.info("event_definition_tag_get_end", tags_count=len(createables))
    num_event_definition_tags = len(createables)

    # Collect property definition tags and taggeditems
    property_definition_paginator = Paginator(
        EnterprisePropertyDefinition.objects.exclude(
            Q(deprecated_tags__isnull=True) | Q(deprecated_tags=[]),
        )
        .order_by("updated_at")
        .values_list("deprecated_tags", "team_id", "id"),
        batch_size,
    )

    for property_definition_page in property_definition_paginator.page_range:
        logger.info(
            "property_definition_tag_batch_get_start",
            limit=batch_size,
            offset=(property_definition_page - 1) * batch_size,
        )
        property_definitions = iter(property_definition_paginator.get_page(property_definition_page))
        for tags, team_id, property_definition_id in property_definitions:
            unique_tags = {tagify(t) for t in tags if isinstance(t, str) and t.strip() != ""}
            for tag in unique_tags:
                temp_tag = Tag(name=tag, team_id=team_id)
                createables.append(
                    (
                        temp_tag,
                        TaggedItem(
                            property_definition_id=property_definition_id,
                            tag_id=temp_tag.id,
                        ),
                    )
                )

    logger.info(
        "property_definition_tag_get_end",
        tags_count=len(createables) - num_event_definition_tags,
    )

    # Consistent ordering to make independent runs non-deterministic
    createables = sorted(createables, key=lambda pair: pair[0].name)

    # Attempts to create tags in bulk while ignoring conflicts. bulk_create does not return any data
    # about which tags were ignored and created, so we must take care of this manually.
    tags_to_create = [tag for (tag, _) in createables]
    Tag.objects.bulk_create(tags_to_create, ignore_conflicts=True, batch_size=batch_size)
    logger.info("tags_bulk_created")

    # Associate tag ids with tagged_item objects in batches. Best case scenario all tags are new. Worst case
    # scenario, all tags already exist and get is made for every tag.
    for offset in range(0, len(tags_to_create), batch_size):
        logger.info("tagged_item_batch_create_start", limit=batch_size, offset=offset)
        batch = tags_to_create[offset : (offset + batch_size)]

        # Find tags that were created, and not already existing
        created_tags = Tag.objects.in_bulk([t.id for t in batch])

        # Tags that are in `tags_to_create` but not in `created_tags` are tags that already exist
        # in the db and must be fetched individually.
        createable_batch = createables[offset : (offset + batch_size)]
        for tag, tagged_item in createable_batch:
            if tag.id in created_tags:
                tagged_item.tag_id = created_tags[tag.id].id
            else:
                tagged_item.tag_id = Tag.objects.filter(name=tag.name, team_id=tag.team_id).first().id

        # Create tag <-> item relationships, ignoring conflicts
        TaggedItem.objects.bulk_create(
            [tagged_item for (_, tagged_item) in createable_batch],
            ignore_conflicts=True,
            batch_size=batch_size,
        )

    logger.info("ee/0012_migrate_tags_v2_end")


def reverse(apps, schema_editor):
    TaggedItem = apps.get_model("posthog", "TaggedItem")
    TaggedItem.objects.filter(Q(event_definition_id__isnull=False) | Q(property_definition_id__isnull=False)).delete()
    # Cascade deletes tag objects


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("ee", "0011_add_tags_back"),
        ("posthog", "0218_uniqueness_constraint_tagged_items"),
    ]

    operations = [migrations.RunPython(forwards, reverse)]
