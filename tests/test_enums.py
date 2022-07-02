from chartparse.enums import AllValuesGettableEnum


class TestAllValuesGettableEnum(object):
    class TrinketEnum(AllValuesGettableEnum):
        ONE = 1
        TWO = 2
        TOO = 2

    class TrinketEnumWithAlias(AllValuesGettableEnum):
        ONE = 1
        TWO = 2
        TOO = 2

    def test_all_values(self):
        assert self.TrinketEnum.all_values() == (1, 2)

    def test_all_values_does_not_get_aliases(self):
        assert self.TrinketEnumWithAlias.all_values() == (1, 2)
