from django.shortcuts import reverse

import pytest
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import AIField


@pytest.mark.django_db
@pytest.mark.field_ai
def test_create_ai_field_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    data_fixture.create_text_field(table=table, order=1, name="name")

    handler = FieldHandler()
    ai_field = handler.create_field(
        user=user,
        table=table,
        type_name="ai",
        name="ai_1",
        ai_generative_ai_type="test_generative_ai",
        ai_generative_ai_model="test_1",
        ai_prompt="'Who are you?'",
    )

    assert ai_field.ai_generative_ai_type == "test_generative_ai"
    assert ai_field.ai_generative_ai_model == "test_1"
    assert ai_field.ai_prompt == "'Who are you?'"
    assert len(AIField.objects.all()) == 1


@pytest.mark.django_db
@pytest.mark.field_ai
def test_update_ai_field_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_ai_field(table=table, order=1, name="name")

    handler = FieldHandler()
    ai_field = handler.update_field(
        user=user,
        field=field,
        name="ai_1",
        ai_generative_ai_type="test_generative_ai",
        ai_generative_ai_model="test_1",
        ai_prompt="'Who are you?'",
    )

    assert ai_field.ai_generative_ai_type == "test_generative_ai"
    assert ai_field.ai_generative_ai_model == "test_1"
    assert ai_field.ai_prompt == "'Who are you?'"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_delete_ai_field_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_ai_field(
        table=table,
        order=1,
        name="name",
        ai_generative_ai_type="test_generative_ai",
        ai_generative_ai_model="test_1",
        ai_prompt="'Who are you?'",
    )

    handler = FieldHandler()
    handler.delete_field(user=user, field=field)

    assert len(AIField.objects.all()) == 0


@pytest.mark.django_db
@pytest.mark.field_ai
def test_create_ai_field_type_via_api(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    data_fixture.create_text_field(table=table, order=1, name="name")

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {
            "name": "Test 1",
            "type": "ai",
            "ai_generative_ai_type": "test_generative_ai",
            "ai_generative_ai_model": "test_1",
            "ai_prompt": "'Who are you?'",
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["ai_generative_ai_type"] == "test_generative_ai"
    assert response_json["ai_generative_ai_model"] == "test_1"
    assert response_json["ai_prompt"] == "'Who are you?'"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_create_ai_field_type_via_api_invalid_formula(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    data_fixture.create_text_field(table=table, order=1, name="name")

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {
            "name": "Test 1",
            "type": "ai",
            "ai_generative_ai_type": "test_generative_ai",
            "ai_generative_ai_model": "test_1",
            "ai_prompt": "ffff;;s9(",
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    response_json = response.json()
    assert response_json["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response_json["detail"]["ai_prompt"][0]["code"] == "invalid"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_create_ai_field_type_via_api_with_invalid_type(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    data_fixture.create_text_field(table=table, order=1, name="name")

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {
            "name": "Test 1",
            "type": "ai",
            "ai_generative_ai_type": "does_not_exist",
            "ai_generative_ai_model": "test_1",
            "ai_prompt": "'Who are you?'",
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_GENERATIVE_AI_DOES_NOT_EXIST"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_create_ai_field_type_via_api_with_invalid_model(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    data_fixture.create_text_field(table=table, order=1, name="name")

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {
            "name": "Test 1",
            "type": "ai",
            "ai_generative_ai_type": "test_generative_ai",
            "ai_generative_ai_model": "does_not_exist",
            "ai_prompt": "'Who are you?'",
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_update_ai_field_type_via_api_with_invalid_type(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    field = data_fixture.create_ai_field(table=table, order=1, name="name")

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        {"ai_generative_ai_type": "does_not_exist"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_GENERATIVE_AI_DOES_NOT_EXIST"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_update_ai_field_type_via_api_with_invalid_model(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    field = data_fixture.create_ai_field(table=table, order=1, name="name")

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        {"ai_generative_ai_model": "does_not_exist"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_MODEL_DOES_NOT_BELONG_TO_TYPE"


@pytest.mark.django_db
@pytest.mark.field_ai
def test_update_ai_field_type_via_api_with_valid_model(data_fixture, api_client):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.register_fake_generate_ai_type()
    field = data_fixture.create_ai_field(table=table, order=1, name="name")

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        {"ai_generative_ai_model": "test_1"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_200_OK

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        {"ai_generative_ai_type": "test_generative_ai"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_200_OK