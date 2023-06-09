from datetime import datetime
from decimal import Decimal
from time import time
from unittest.mock import MagicMock

from django.conf import settings
from django.core.cache import caches
from django.db import models
from django.test import override_settings
from django.utils.timezone import make_aware, utc

import pytest
from cachalot.settings import cachalot_settings

from baserow.contrib.database.fields.exceptions import (
    FilterFieldNotFound,
    OrderByFieldNotFound,
    OrderByFieldNotPossible,
)
from baserow.contrib.database.table.models import Table
from baserow.contrib.database.views.exceptions import (
    ViewFilterTypeDoesNotExist,
    ViewFilterTypeNotAllowedForField,
)


@pytest.mark.django_db
def test_workspace_user_get_next_order(data_fixture):
    database = data_fixture.create_database_application()
    database_2 = data_fixture.create_database_application()
    data_fixture.create_database_table(order=1, database=database)
    data_fixture.create_database_table(order=2, database=database)
    data_fixture.create_database_table(order=10, database=database_2)

    assert Table.get_last_order(database) == 3
    assert Table.get_last_order(database_2) == 11


@pytest.mark.django_db
def test_get_table_model(data_fixture):
    default_model_fields_count = 4
    table = data_fixture.create_database_table(name="Cars")
    text_field = data_fixture.create_text_field(
        table=table, order=0, name="Color", text_default="white"
    )
    number_field = data_fixture.create_number_field(
        table=table, order=1, name="Horsepower"
    )
    boolean_field = data_fixture.create_boolean_field(
        table=table, order=2, name="For sale"
    )

    model = table.get_model(attribute_names=True)
    assert model.__name__ == f"Table{table.id}Model"
    assert model._generated_table_model
    assert model._meta.db_table == f"database_table_{table.id}"
    assert len(model._meta.get_fields()) == 4 + default_model_fields_count

    color_field = model._meta.get_field("color")
    horsepower_field = model._meta.get_field("horsepower")
    for_sale_field = model._meta.get_field("for_sale")

    assert isinstance(color_field, models.TextField)
    assert color_field.verbose_name == "Color"
    assert color_field.db_column == f"field_{text_field.id}"
    assert color_field.default == "white"
    assert color_field.null

    assert isinstance(horsepower_field, models.DecimalField)
    assert horsepower_field.verbose_name == "Horsepower"
    assert horsepower_field.db_column == f"field_{number_field.id}"
    assert horsepower_field.null

    assert isinstance(for_sale_field, models.BooleanField)
    assert for_sale_field.verbose_name == "For sale"
    assert for_sale_field.db_column == f"field_{boolean_field.id}"
    assert not for_sale_field.default

    table_2 = data_fixture.create_database_table(name="House")
    data_fixture.create_number_field(
        table=table_2,
        order=0,
        name="Sale price",
        number_decimal_places=3,
        number_negative=True,
    )

    model = table_2.get_model(attribute_names=True)
    sale_price_field = model._meta.get_field("sale_price")
    assert isinstance(sale_price_field, models.DecimalField)
    assert sale_price_field.decimal_places == 3
    assert sale_price_field.null

    model_2 = table.get_model(
        fields=[number_field], field_ids=[text_field.id], attribute_names=True
    )
    assert len(model_2._meta.get_fields()) == 3 + default_model_fields_count

    color_field = model_2._meta.get_field("color")
    assert color_field
    assert color_field.db_column == f"field_{text_field.id}"

    horsepower_field = model_2._meta.get_field("horsepower")
    assert horsepower_field
    assert horsepower_field.db_column == f"field_{number_field.id}"

    model_3 = table.get_model()
    assert model_3._meta.db_table == f"database_table_{table.id}"
    assert len(model_3._meta.get_fields()) == 4 + default_model_fields_count

    field_1 = model_3._meta.get_field(f"field_{text_field.id}")
    assert isinstance(field_1, models.TextField)
    assert field_1.db_column == f"field_{text_field.id}"

    field_2 = model_3._meta.get_field(f"field_{number_field.id}")
    assert isinstance(field_2, models.DecimalField)
    assert field_2.db_column == f"field_{number_field.id}"

    field_3 = model_3._meta.get_field(f"field_{boolean_field.id}")
    assert isinstance(field_3, models.BooleanField)
    assert field_3.db_column == f"field_{boolean_field.id}"

    text_field_2 = data_fixture.create_text_field(
        table=table, order=3, name="Color", text_default="orange"
    )
    model = table.get_model(attribute_names=True)
    field_names = [f.name for f in model._meta.get_fields()]
    assert len(field_names) == 5 + default_model_fields_count
    assert f"{text_field.model_attribute_name}_field_{text_field.id}" in field_names
    assert f"{text_field_2.model_attribute_name}_field_{text_field.id}" in field_names

    # Test if the fields are also returns if requested.
    model = table.get_model()
    fields = model._field_objects
    assert len(fields.items()) == 4

    assert fields[text_field.id]["field"].id == text_field.id
    assert fields[text_field.id]["type"].type == "text"
    assert fields[text_field.id]["name"] == f"field_{text_field.id}"

    assert fields[number_field.id]["field"].id == number_field.id
    assert fields[number_field.id]["type"].type == "number"
    assert fields[number_field.id]["name"] == f"field_{number_field.id}"

    assert fields[boolean_field.id]["field"].id == boolean_field.id
    assert fields[boolean_field.id]["type"].type == "boolean"
    assert fields[boolean_field.id]["name"] == f"field_{boolean_field.id}"

    assert fields[text_field_2.id]["field"].id == text_field_2.id
    assert fields[text_field_2.id]["type"].type == "text"
    assert fields[text_field_2.id]["name"] == f"field_{text_field_2.id}"


@pytest.mark.django_db
def test_get_table_model_to_str(data_fixture):
    table = data_fixture.create_database_table()
    table_without_primary = data_fixture.create_database_table()
    text_field = data_fixture.create_text_field(table=table, primary=True)

    model = table.get_model()
    instance = model.objects.create(**{f"field_{text_field.id}": "Value"})
    assert str(instance) == "Value"

    model_without_primary = table_without_primary.get_model()
    instance = model_without_primary.objects.create()
    assert str(instance) == f"unnamed row {instance.id}"


@pytest.mark.django_db
def test_enhance_by_fields_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    field = data_fixture.create_text_field(table=table, order=0, name="Color")

    model = table.get_model(attribute_names=True)
    mocked_type = MagicMock()

    model._field_objects[field.id]["type"] = mocked_type
    model.objects.all().enhance_by_fields()

    mocked_type.enhance_queryset.assert_called()


@pytest.mark.django_db
def test_search_all_fields_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    data_fixture.create_text_field(table=table, order=0, name="Name")
    data_fixture.create_text_field(table=table, order=1, name="Color")
    data_fixture.create_number_field(table=table, order=2, name="Price")
    data_fixture.create_long_text_field(table=table, order=3, name="Description")
    data_fixture.create_date_field(table=table, order=4, name="Date", date_format="EU")
    data_fixture.create_date_field(
        table=table,
        order=5,
        name="DateTime",
        date_format="US",
        date_include_time=True,
        date_time_format="24",
    )
    data_fixture.create_file_field(table=table, order=6, name="File")
    select = data_fixture.create_single_select_field(
        table=table, order=7, name="select"
    )
    option_a = data_fixture.create_select_option(
        field=select, value="Option A", color="blue"
    )
    option_b = data_fixture.create_select_option(
        field=select, value="Option B", color="red"
    )
    data_fixture.create_phone_number_field(table=table, order=8, name="PhoneNumber")

    model = table.get_model(attribute_names=True)
    row_1 = model.objects.create(
        name="BMW",
        color="Blue",
        price="10000",
        description="This is the fastest car there is.",
        date="0005-05-05",
        datetime=make_aware(datetime(4006, 7, 8, 0, 0, 0), utc),
        file=[{"visible_name": "test_file.png"}],
        select=option_a,
        phonenumber="99999",
    )
    row_2 = model.objects.create(
        name="Audi",
        color="Orange",
        price="20500",
        description="This is the most expensive car we have.",
        date="2005-05-05",
        datetime=make_aware(datetime(5, 5, 5, 0, 48, 0), utc),
        file=[{"visible_name": "other_file.png"}],
        select=option_b,
        phonenumber="++--999999",
    )
    row_3 = model.objects.create(
        name="Volkswagen",
        color="White",
        price="5000",
        description="The oldest car that we have.",
        date="9999-05-05",
        datetime=make_aware(datetime(5, 5, 5, 9, 59, 0), utc),
        file=[],
        phonenumber="",
    )

    results = model.objects.all().search_all_fields("FASTEST")
    assert row_1 in results

    results = model.objects.all().search_all_fields("car")
    assert len(results) == 3
    assert row_1 in results
    assert row_2 in results
    assert row_3 in results

    results = model.objects.all().search_all_fields("oldest")
    assert len(results) == 1
    assert row_3 in results

    results = model.objects.all().search_all_fields("Audi")
    assert len(results) == 1
    assert row_2 in results

    results = model.objects.all().search_all_fields(str(row_1.id))
    assert len(results) == 1
    assert row_1 in results

    results = model.objects.all().search_all_fields(str(row_3.id))
    assert len(results) == 1
    assert row_3 in results

    results = model.objects.all().search_all_fields("500")
    assert len(results) == 2
    assert row_2 in results
    assert row_3 in results

    results = model.objects.all().search_all_fields("0" + str(row_1.id))
    assert len(results) == 0

    results = model.objects.all().search_all_fields("05/05/9999")
    assert len(results) == 1
    assert row_3 in results

    results = model.objects.all().search_all_fields("07/08/4006")
    assert len(results) == 1
    assert row_1 in results

    results = model.objects.all().search_all_fields("00:")
    assert len(results) == 2
    assert row_1 in results
    assert row_2 in results

    results = model.objects.all().search_all_fields(".png")
    assert len(results) == 2
    assert row_1 in results
    assert row_2 in results

    results = model.objects.all().search_all_fields("test_file")
    assert len(results) == 1
    assert row_1 in results

    results = model.objects.all().search_all_fields("Option")
    assert len(results) == 2
    assert row_1 in results
    assert row_2 in results

    results = model.objects.all().search_all_fields("Option B")
    assert len(results) == 1
    assert row_2 in results

    results = model.objects.all().search_all_fields("999999")
    assert len(results) == 1
    assert row_2 in results

    results = model.objects.all().search_all_fields("99999")
    assert len(results) == 2
    assert row_1 in results
    assert row_2 in results

    results = model.objects.all().search_all_fields("white car")
    assert len(results) == 0


@pytest.mark.django_db
def test_order_by_fields_string_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    table_2 = data_fixture.create_database_table(database=table.database)
    name_field = data_fixture.create_text_field(table=table, order=0, name="Name")
    color_field = data_fixture.create_text_field(table=table, order=1, name="Color")
    price_field = data_fixture.create_number_field(table=table, order=2, name="Price")
    description_field = data_fixture.create_long_text_field(
        table=table, order=3, name="Description"
    )
    link_field = data_fixture.create_link_row_field(table=table, link_row_table=table_2)
    single_select_field = data_fixture.create_single_select_field(
        table=table, name="Single"
    )
    multiple_select_field = data_fixture.create_multiple_select_field(
        table=table, name="Multi"
    )

    option_a = data_fixture.create_select_option(
        field=single_select_field, value="A", color="blue"
    )
    option_b = data_fixture.create_select_option(
        field=single_select_field, value="B", color="red"
    )
    option_c = data_fixture.create_select_option(
        field=single_select_field, value="C", color="blue"
    )
    option_d = data_fixture.create_select_option(
        field=single_select_field, value="D", color="red"
    )

    model = table.get_model(attribute_names=True)
    row_1 = model.objects.create(
        name="BMW",
        color="Blue",
        price=10000,
        description="Sports car.",
        single=option_a,
    )
    getattr(row_1, "multi").set([option_c.id])
    row_2 = model.objects.create(
        name="Audi",
        color="Orange",
        price=20000,
        description="This is the most expensive car we have.",
        single=option_b,
    )
    getattr(row_2, "multi").set([option_d.id])
    row_3 = model.objects.create(
        name="Volkswagen", color="White", price=5000, description="A very old car."
    )
    row_4 = model.objects.create(
        name="Volkswagen", color="Green", price=4000, description="Strange color."
    )

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string("xxxx")

    with pytest.raises(ValueError):
        model.objects.all().order_by_fields_string("")

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string("id")

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string("field_99999")

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string(f"{name_field.name}")

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string(
            f"field_{name_field.id}", only_order_by_field_ids=[]
        )

    with pytest.raises(OrderByFieldNotPossible):
        model.objects.all().order_by_fields_string(f"field_{link_field.id}")

    results = model.objects.all().order_by_fields_string(f"-field_{price_field.id}")
    assert results[0].id == row_2.id
    assert results[1].id == row_1.id
    assert results[2].id == row_3.id
    assert results[3].id == row_4.id

    results = model.objects.all().order_by_fields_string(
        f"field_{name_field.id},-field_{price_field.id}"
    )
    assert results[0].id == row_2.id
    assert results[1].id == row_1.id
    assert results[2].id == row_3.id
    assert results[3].id == row_4.id

    results = model.objects.all().order_by_fields_string(
        f"{description_field.id},-field_{color_field.id}"
    )
    assert results[0].id == row_3.id
    assert results[1].id == row_1.id
    assert results[2].id == row_4.id
    assert results[3].id == row_2.id

    row_5 = model.objects.create(
        name="Audi",
        color="Red",
        price=2000,
        description="Old times",
        order=Decimal("0.1"),
    )

    row_2.order = Decimal("0.1")
    results = model.objects.all().order_by_fields_string(f"{name_field.id}")
    assert results[0].id == row_5.id
    assert results[1].id == row_2.id
    assert results[2].id == row_1.id
    assert results[3].id == row_3.id
    assert results[4].id == row_4.id

    results = model.objects.all().order_by_fields_string(f"{single_select_field.id}")
    assert results[0].id == row_5.id
    assert results[1].id == row_3.id
    assert results[2].id == row_4.id
    assert results[3].id == row_1.id
    assert results[4].id == row_2.id

    results = model.objects.all().order_by_fields_string(
        f"-field_{single_select_field.id}"
    )
    assert results[0].id == row_2.id
    assert results[1].id == row_1.id
    assert results[2].id == row_5.id
    assert results[3].id == row_3.id
    assert results[4].id == row_4.id

    results = model.objects.all().order_by_fields_string(f"{multiple_select_field.id}")
    assert results[0].id == row_5.id
    assert results[1].id == row_3.id
    assert results[2].id == row_4.id
    assert results[3].id == row_1.id
    assert results[4].id == row_2.id

    results = model.objects.all().order_by_fields_string(
        f"-field_{multiple_select_field.id}"
    )
    assert results[0].id == row_2.id
    assert results[1].id == row_1.id
    assert results[2].id == row_5.id
    assert results[3].id == row_3.id
    assert results[4].id == row_4.id


@pytest.mark.django_db
def test_order_by_fields_string_queryset_with_user_field_names(data_fixture):
    table, fields, rows = data_fixture.build_table(
        columns=[
            ("Name", "text"),
            ("My Color", "text"),
            ("-Weird FieldName", "number"),
            ("+Another Weird Field", "long_text"),
        ],
        rows=[
            ["BMW", "Blue", 10000, "Sports car."],
            ["Audi", "Orange", 20000, "This is the most expensive car we have."],
            ["Volkswagen", "White", 5000, "A very old car."],
            ["Volkswagen", "Green", 4000, "Strange color."],
        ],
    )
    table_2 = data_fixture.create_database_table(database=table.database)
    link_field = data_fixture.create_link_row_field(
        table=table, link_row_table=table_2, name="Link Field"
    )

    model = table.get_model()

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string("id", user_field_names=True)

    with pytest.raises(OrderByFieldNotFound):
        model.objects.all().order_by_fields_string(
            "Non Existent Field", user_field_names=True
        )

    with pytest.raises(OrderByFieldNotPossible):
        model.objects.all().order_by_fields_string(
            link_field.name, user_field_names=True
        )

    results = model.objects.all().order_by_fields_string(
        f"--Weird FieldName", user_field_names=True
    )
    assert results[0].id == rows[1].id
    assert results[1].id == rows[0].id
    assert results[2].id == rows[2].id
    assert results[3].id == rows[3].id

    results = model.objects.all().order_by_fields_string(
        f"Name,--Weird FieldName", user_field_names=True
    )
    assert results[0].id == rows[1].id
    assert results[1].id == rows[0].id
    assert results[2].id == rows[2].id
    assert results[3].id == rows[3].id

    results = model.objects.all().order_by_fields_string(
        f"++Another Weird Field,My Color", user_field_names=True
    )
    assert results[0].id == rows[2].id
    assert results[1].id == rows[0].id
    assert results[2].id == rows[3].id
    assert results[3].id == rows[1].id

    row_5 = model.objects.create(
        **{
            f"field_{fields[0].id}": "Audi",
            f"field_{fields[1].id}": 2000,
            f"field_" f"{fields[3].id}": "Old times",
            "order": Decimal("0.1"),
        }
    )

    rows[1].order = Decimal("0.1")
    results = model.objects.all().order_by_fields_string(f"Name", user_field_names=True)
    assert results[0].id == row_5.id
    assert results[1].id == rows[1].id
    assert results[2].id == rows[0].id
    assert results[3].id == rows[2].id
    assert results[4].id == rows[3].id


@pytest.mark.django_db
def test_filter_by_fields_object_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    data_fixture.create_database_table(database=table.database)
    name_field = data_fixture.create_text_field(table=table, order=0, name="Name")
    data_fixture.create_text_field(table=table, order=1, name="Color")
    price_field = data_fixture.create_number_field(table=table, order=2, name="Price")
    active_field = data_fixture.create_boolean_field(
        table=table, order=2, name="Active"
    )
    description_field = data_fixture.create_long_text_field(
        table=table, order=3, name="Description"
    )

    model = table.get_model(attribute_names=True)
    row_1 = model.objects.create(
        name="BMW", color="Blue", price=10000, description="Sports car."
    )
    row_2 = model.objects.create(
        name="Audi",
        color="Orange",
        price=20000,
        description="This is the most expensive car we have.",
    )
    model.objects.create(
        name="Volkswagen", color="White", price=5000, description="A very old car."
    )
    row_4 = model.objects.create(
        name="Volkswagen", color="Green", price=4000, description=""
    )

    with pytest.raises(ValueError):
        model.objects.all().filter_by_fields_object(
            filter_object={
                f"filter__field_999999__equal": ["BMW"],
            },
            filter_type="RANDOM",
        )

    with pytest.raises(FilterFieldNotFound):
        model.objects.all().filter_by_fields_object(
            filter_object={
                f"filter__field_999999__equal": ["BMW"],
            },
            filter_type="AND",
        )

    with pytest.raises(FilterFieldNotFound):
        model.objects.all().filter_by_fields_object(
            filter_object={
                f"filter__field_{name_field.id}__equal": ["BMW"],
            },
            filter_type="AND",
            only_filter_by_field_ids=[],
        )

    with pytest.raises(ViewFilterTypeDoesNotExist):
        model.objects.all().filter_by_fields_object(
            filter_object={
                f"filter__field_{name_field.id}__INVALID": ["BMW"],
            },
            filter_type="AND",
        )

    with pytest.raises(ViewFilterTypeNotAllowedForField):
        model.objects.all().filter_by_fields_object(
            filter_object={
                f"filter__field_{active_field.id}__contains": "10",
            },
            filter_type="AND",
        )

    # All the entries are not following the correct format and should be ignored.
    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__not__equal": ["BMW"],
            f"filter__field_{price_field.id}_equal": "10000",
            f"filters__field_{price_field.id}__equal": "10000",
        },
        filter_type="AND",
    )
    assert len(results) == 4

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_{name_field.id}__equal": ["BMW"],
            f"filter__field_{price_field.id}__equal": "10000",
        },
        filter_type="AND",
    )
    assert len(results) == 1
    assert results[0].id == row_1.id

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_{name_field.id}__equal": ["BMW", "Audi"],
        },
        filter_type="AND",
    )
    assert len(results) == 0

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_{name_field.id}__equal": ["BMW", "Audi"],
        },
        filter_type="OR",
    )
    assert len(results) == 2
    assert results[0].id == row_1.id
    assert results[1].id == row_2.id

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_{price_field.id}__higher_than": "5500",
        },
        filter_type="AND",
    )
    assert len(results) == 2
    assert results[0].id == row_1.id
    assert results[1].id == row_2.id

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_{description_field.id}__empty": "",
        },
        filter_type="AND",
    )
    assert len(results) == 1
    assert results[0].id == row_4.id


@pytest.mark.django_db
def test_filter_by_fields_object_with_created_on_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")

    model = table.get_model()

    row_1 = model.objects.create()
    row_1.created_on = datetime(2021, 1, 1, 12, 0, 0, tzinfo=utc)
    row_1.save()

    row_2 = model.objects.create()
    row_2.created_on = datetime(2021, 1, 2, 12, 0, 0, tzinfo=utc)
    row_2.save()

    row_3 = model.objects.create()
    row_3.created_on = datetime(2021, 1, 3, 12, 0, 0, tzinfo=utc)
    row_3.save()

    print(row_1.created_on)
    print(row_2.created_on)
    print(row_3.created_on)

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_created_on__date_after": "2021-01-02 13:00",
        },
        filter_type="AND",
    )
    assert len(results) == 1
    assert results[0].id == row_3.id


@pytest.mark.django_db
def test_filter_by_fields_object_with_updated_on_queryset(data_fixture):
    table = data_fixture.create_database_table(name="Cars")

    model = table.get_model()

    row_1 = model.objects.create()
    row_2 = model.objects.create()
    row_3 = model.objects.create()

    model.objects.filter(id=row_1.id).update(
        updated_on=datetime(2021, 1, 1, 12, 0, 0, tzinfo=utc)
    )
    model.objects.filter(id=row_2.id).update(
        updated_on=datetime(2021, 1, 2, 12, 0, 0, tzinfo=utc)
    )
    model.objects.filter(id=row_3.id).update(
        updated_on=datetime(2021, 1, 3, 12, 0, 0, tzinfo=utc)
    )

    results = model.objects.all().filter_by_fields_object(
        filter_object={
            f"filter__field_updated_on__date_before": "2021-01-02 12:00",
        },
        filter_type="AND",
    )
    assert len(results) == 1
    assert results[0].id == row_1.id


@pytest.mark.django_db
def test_table_model_fields_requiring_refresh_on_insert(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    data_fixture.create_text_field(table=table, name="Color", text_default="white")
    model = table.get_model()
    assert model.fields_requiring_refresh_after_insert() == []

    data_fixture.create_formula_field(
        table=table, name="Formula", formula="'a'", formula_type="text"
    )
    model_with_normal_formula_field = table.get_model()
    fields_from_normal_formula_model = (
        model_with_normal_formula_field.fields_requiring_refresh_after_insert()
    )
    assert fields_from_normal_formula_model == []

    field_needing_refresh = data_fixture.create_formula_field(
        table=table,
        name="Formula2",
        formula="row_id()",
        formula_type="number",
        number_decimal_places=0,
    )
    model_with_normal_formula_field = table.get_model()
    fields_from_model_with_row_id_formula = (
        model_with_normal_formula_field.fields_requiring_refresh_after_insert()
    )
    assert len(fields_from_model_with_row_id_formula) == 1
    assert (
        fields_from_model_with_row_id_formula[0] == f"field_{field_needing_refresh.id}"
    )


@pytest.mark.django_db
def test_table_model_fields_requiring_refresh_after_update(data_fixture):
    table = data_fixture.create_database_table(name="Cars")
    data_fixture.create_text_field(table=table, name="Color", text_default="white")
    model = table.get_model()
    assert model.fields_requiring_refresh_after_update() == []

    formula_field = data_fixture.create_formula_field(
        table=table, name="Formula", formula="'a'", formula_type="text"
    )
    model_with_normal_formula_field = table.get_model()
    fields_from_normal_formula_model = (
        model_with_normal_formula_field.fields_requiring_refresh_after_update()
    )
    assert len(fields_from_normal_formula_model) == 1
    assert fields_from_normal_formula_model[0] == f"field_{formula_field.id}"


@pytest.mark.django_db
def test_order_by_field_string_with_multiple_field_types_requiring_aggregations(
    data_fixture,
):
    table = data_fixture.create_database_table(name="Cars")
    multiple_select_field_a = data_fixture.create_multiple_select_field(
        table=table, name="Multi A"
    )
    multiple_select_field_b = data_fixture.create_multiple_select_field(
        table=table, name="Multi B"
    )

    option_a = data_fixture.create_select_option(
        field=multiple_select_field_a, value="A", color="blue"
    )
    option_b = data_fixture.create_select_option(
        field=multiple_select_field_a, value="B", color="red"
    )
    option_c = data_fixture.create_select_option(
        field=multiple_select_field_b, value="C", color="blue"
    )
    option_d = data_fixture.create_select_option(
        field=multiple_select_field_b, value="D", color="red"
    )

    model = table.get_model(attribute_names=True)
    row_1 = model.objects.create()
    getattr(row_1, "multi_a").set([option_a.id])
    getattr(row_1, "multi_b").set([option_c.id])
    row_2 = model.objects.create()
    getattr(row_2, "multi_a").set([option_b.id])
    getattr(row_2, "multi_b").set([option_d.id])

    results = model.objects.all().order_by_fields_string(
        f"field_{multiple_select_field_a.id},-field_{multiple_select_field_b.id}"
    )
    assert results[0].id == row_1.id
    assert results[1].id == row_2.id


@pytest.mark.django_db
def test_table_hierarchy(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    app = data_fixture.create_database_application(workspace=workspace, name="Test 1")
    table = data_fixture.create_database_table(name="Cars", database=app)

    assert table.get_parent() == app
    assert table.get_root() == workspace

    table_model = table.get_model()
    row = table_model.objects.create()
    assert row.get_parent() == table
    assert row.get_root() == workspace


@override_settings(CACHALOT_ENABLED=True)
@pytest.mark.django_db(transaction=True)
def test_cachalot_cache_only_count_query_correctly(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    app = data_fixture.create_database_application(workspace=workspace, name="Test 1")
    table = data_fixture.create_database_table(name="Cars", database=app)
    cache = caches[settings.CACHALOT_CACHE]

    queries = {}

    def get_mocked_query_cache_key(compiler):
        sql, _ = compiler.as_sql()
        sql_lower = sql.lower()
        if "count(*)" in sql_lower:
            key = "count"
        elif f"database_table_{table.id}" in sql_lower:
            key = "select_table"
        else:
            key = f"{time()}"
        queries[key] = sql_lower
        return key

    cachalot_settings.CACHALOT_QUERY_KEYGEN = get_mocked_query_cache_key
    cachalot_settings.CACHALOT_TABLE_KEYGEN = lambda _, table: table.rsplit("_", 1)[1]

    table_model = table.get_model()
    row = table_model.objects.create()

    # listing items should not cache the result
    assert [r.id for r in table_model.objects.all()] == [row.id]
    assert cache.get("select_table") is None, queries["select_table"]

    def assert_cachalot_cache_queryset_count_of(expected_count):
        # count() should save the result of the query in the cache
        assert table_model.objects.count() == expected_count

        # the count query has been cached
        inserted_cache_entry = cache.get("count")
        assert inserted_cache_entry is not None
        assert inserted_cache_entry[1][0] == expected_count

    assert_cachalot_cache_queryset_count_of(1)

    # creating a new row should invalidate the cache result
    table_model.objects.create()

    # cachalot invalidate the cache by setting the timestamp for the table
    # greater than the timestamp of the cache entry
    invalidation_timestamp = cache.get(table.id)
    assert invalidation_timestamp > cache.get("count")[0]

    assert_cachalot_cache_queryset_count_of(2)
