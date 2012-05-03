from django.test import TestCase

from hamcrest import *
from django_dynamic_fixture import get

from core.rules import ApplyRules, is_rule_matching

from sample.models import *
from sample.rules import *
from sample.groups import *

from django.contrib.auth.models import User
from core.models import Group, ACL

class TestRules(TestCase):

    def setUp(self):
        Group.default = None

        self.customer = User.objects.create(username="customer")
        self.rep = User.objects.create(username="rep")
        self.admin = User.objects.create(username="admin")
        self.anonymous = User.objects.create(username="anonymous")

        Group.register(CustomerGroup)
        Group.register(AdminGroup)
        Group.register(RepGroup)

        Rule.register(CanSeeAnyProducts)
        Rule.register(CanSeeCProducts, type=ACL.DENY, action="can_see")
        Rule.register(CanMasquerade)
        Rule.register(CanMasqueradeAsCustomer)

        ACL.objects.create(group="customergroup", rule="can_see_products", action="can_see", type=ACL.ALLOW)
        ACL.objects.create(group="admingroup", rule="can_see_C", action="can_see", type=ACL.DENY)
        ACL.objects.create(group="admingroup", rule="can_see_products", action="can_see", type=ACL.ALLOW)

        ACL.objects.create(group="rep", rule="can_masquerade_as_any", action="masquerade", type=ACL.ALLOW)
        ACL.objects.create(group="admingroup", rule="can_masquerade_as_customer", action="masquerade", type=ACL.ALLOW)

        for product_type in ["A", "B", "C"]:
            get(Product, product_type=product_type)

    def test_acceptance_rules(self):
        """
        Given 2 users being in 2 groups (customer and productAdmin) and a list of A, B and C products,
            the user 1 sees A and B product
            the user 2 sees A, B and C
        """
        assert_that( ApplyRules(on=Product.objects.all(), action="can_see", for_=self.anonymous).check().count(), is_(0))
        assert_that( ApplyRules(on=Product.objects.all(), action="can_see", for_=self.admin).check().count(), is_(3))
        assert_that( ApplyRules(on=Product.objects.all(), action="can_see", for_=self.customer).check().count(), is_(2))

        product_A = Product.objects.get(product_type="A")
        assert_that( is_rule_matching(on=product_A, action="can_see", for_=self.anonymous), is_(False))
        assert_that( is_rule_matching(on=product_A, action="can_see", for_=self.customer), is_(True))

        product_C = Product.objects.get(product_type="C")
        assert_that( is_rule_matching(on=product_C, action="can_see", for_=self.customer), is_(False))
        assert_that( is_rule_matching(on=product_C, action="can_see", for_=self.admin), is_(True))

    def test_acceptance_masquerading(self):
        assert_that( is_rule_matching(on=self.customer, action="masquerade", for_=self.customer), is_(False))
        assert_that( is_rule_matching(on=self.customer, action="masquerade", for_=self.rep), is_(True))
        assert_that( is_rule_matching(on=self.customer, action="masquerade", for_=self.admin), is_(True))

        assert_that( is_rule_matching(on=self.admin, action="masquerade", for_=self.rep), is_(True))
        assert_that( is_rule_matching(on=self.customer, action="masquerade", for_=self.rep), is_(True))
        assert_that( is_rule_matching(on=self.rep, action="masquerade", for_=self.rep), is_(True))

        assert_that( is_rule_matching(on=self.admin, action="masquerade", for_=self.admin), is_(False))

    def test_belong_to_group(self):
        assert_that( CustomerGroup.belong(self.customer), is_(True))
        assert_that( CustomerGroup.belong(self.admin), is_(False))
        assert_that( AdminGroup.belong(self.customer), is_(False))
        assert_that( AdminGroup.belong(self.admin), is_(True))

    def test_get_group(self):
        assert_that( Group.get_groups(self.customer), is_(['customergroup']))
        assert_that( Group.get_groups(self.admin), is_(['admingroup']))

    def test_get_group_by_name(self):
       assert_that( Group.get_by_name("customergroup") == CustomerGroup)

