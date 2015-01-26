# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
#
# This file is part of Stalker.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
import tempfile
import unittest
import datetime
from stalker import (db, defaults, Project, Status, StatusList, Type,
                     Repository, User, Budget, BudgetEntry)


class BudgetTestBase(unittest.TestCase):
    """the base for this test
    """

    def setUp(self):
        """run once
        """
        defaults.timing_resolution = datetime.timedelta(hours=1)

        # create a new session
        db.setup({
            'sqlalchemy.url': 'sqlite://',
            'sqlalchemy.echo': False
        })
        db.init()

        self.status_wfd = Status.query.filter_by(code="WFD").first()
        self.status_rts = Status.query.filter_by(code="RTS").first()
        self.status_wip = Status.query.filter_by(code="WIP").first()
        self.status_prev = Status.query.filter_by(code="PREV").first()
        self.status_hrev = Status.query.filter_by(code="HREV").first()
        self.status_drev = Status.query.filter_by(code="DREV").first()
        self.status_oh = Status.query.filter_by(code="OH").first()
        self.status_stop = Status.query.filter_by(code="STOP").first()
        self.status_cmpl = Status.query.filter_by(code="CMPL").first()

        self.task_status_list = StatusList.query\
            .filter_by(target_entity_type='Task').first()

        self.test_project_status_list = StatusList(
            name="Project Statuses",
            statuses=[self.status_wip,
                      self.status_prev,
                      self.status_cmpl],
            target_entity_type=Project,
        )

        self.test_movie_project_type = Type(
            name="Movie Project",
            code='movie',
            target_entity_type=Project,
        )

        self.test_repository_type = Type(
            name="Test Repository Type",
            code='test',
            target_entity_type=Repository,
        )

        self.test_repository = Repository(
            name="Test Repository",
            type=self.test_repository_type,
            linux_path=tempfile.mkdtemp(),
            windows_path=tempfile.mkdtemp(),
            osx_path=tempfile.mkdtemp()
        )

        self.test_user1 = User(
            name="User1",
            login="user1",
            email="user1@user1.com",
            password="1234"
        )

        self.test_user2 = User(
            name="User2",
            login="user2",
            email="user2@user2.com",
            password="1234"
        )

        self.test_user3 = User(
            name="User3",
            login="user3",
            email="user3@user3.com",
            password="1234"
        )

        self.test_user4 = User(
            name="User4",
            login="user4",
            email="user4@user4.com",
            password="1234"
        )

        self.test_user5 = User(
            name="User5",
            login="user5",
            email="user5@user5.com",
            password="1234"
        )

        self.test_project = Project(
            name="Test Project1",
            code='tp1',
            type=self.test_movie_project_type,
            status_list=self.test_project_status_list,
            repository=self.test_repository
        )

        self.kwargs = {
            'project': self.test_project,
            'name': 'Test Budget 1'
        }

        self.test_budget = Budget(**self.kwargs)


class BudgetTest(BudgetTestBase):
    """tests the stalker.models.budget.Budget class
    """

    def test_entries_attribute_is_set_to_a_list_of_other_instances_than_a_budget_entry(self):
        """testing if a TypeError will be raised when the entries attribute is
        set to something other than a list of BugdgetEntries.
        """
        with self.assertRaises(TypeError) as cm:
            self.test_budget.entries = ['some', 'string', 1, 2]

        self.assertEqual(
            str(cm.exception),
            'Budget.entries should be a list of BudgetEntry instances, not str'
        )

    def test_entries_attribute_is_working_properly(self):
        """testing if the entries attribute is working properly
        """
        from stalker import BudgetEntry
        some_other_budget = Budget(
            name='Test Budget',
            project=self.test_project
        )
        entry1 = BudgetEntry(budget=some_other_budget)
        entry2 = BudgetEntry(budget=some_other_budget)

        self.test_budget.entries = [entry1, entry2]

        self.assertEqual(
            self.test_budget.entries,
            [entry1, entry2]
        )


class BudgetEntryTestCase(BudgetTestBase):
    """tests the stalker.models.budget.BudgetEntry class
    """

    def test_budget_argument_is_skipped(self):
        """testing if a TypeError will be raised if the budget argument is
        skipped
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(amount=10.0)

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.budget should be a Budget instance, not NoneType'
        )

    def test_budget_argument_is_none(self):
        """testing if a TypeError will be raised if the budget argument is
        None
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=None, amount=10.0)

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.budget should be a Budget instance, not NoneType'
        )

    def test_budget_attribute_is_set_to_none(self):
        """testing if a TypeError will be raised if the budget attribute is
        set to None
        """
        entry = BudgetEntry(
            budget=self.test_budget
        )
        with self.assertRaises(TypeError) as cm:
            entry.budget = None

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.budget should be a Budget instance, not NoneType'
        )

    def test_budget_argument_is_not_a_budget_instance(self):
        """testing if a TypeError will be raised if the budget argument is not
        a Budget instance
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(
                budget='not a budget',
                amount=10.0
            )

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.budget should be a Budget instance, not str'
        )

    def test_budget_attribute_is_not_a_budget_instance(self):
        """testing if a TypeError will be raised if the budget attribute is not
        set to a something that is a Budget instance
        """
        entry = BudgetEntry(budget=self.test_budget, amount=10.0)
        with self.assertRaises(TypeError) as cm:
            entry.budget = 'not a budget instance'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.budget should be a Budget instance, not str'
        )

    def test_budget_argument_is_working_properly(self):
        """testing if the budget argument value is correctly passed to the
        budget attribute
        """
        entry = BudgetEntry(
            budget=self.test_budget,
            amount=10.0
        )
        self.assertEqual(entry.budget, self.test_budget)

    def test_budget_attribute_is_working_properly(self):
        """testing if the budget attribute value can correctly be changed
        """
        entry = BudgetEntry(
            budget=self.test_budget,
            amount=10.0
        )
        new_budget = Budget(name='Test Budget', project=self.test_project)
        self.assertNotEqual(entry.budget, new_budget)
        entry.budget = new_budget
        self.assertEqual(entry.budget, new_budget)

    def test_cost_argument_is_skipped(self):
        """testing if the cost attribute will be 0 if the cost argument is
        skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.cost, 0.0)

    def test_cost_argument_is_set_to_None(self):
        """testing if the cost attribute will be set to 0 if the cost argument
        is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, cost=None)
        self.assertEqual(entry.cost, 0.0)

    def test_cost_attribute_is_set_to_None(self):
        """testing if the cost attribute will be set to 0 if it is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, cost=10.0)
        self.assertEqual(entry.cost, 10.0)
        entry.cost = None
        self.assertEqual(entry.cost, 0.0)

    def test_cost_argument_is_not_a_number(self):
        """testing if a TypeError will be raised if the cost argument is set to
        something other than a number
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, cost='some string')

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.cost should be a number, not str'
        )

    def test_cost_attribute_is_not_a_number(self):
        """testing if a TypeError will be raised if cost attribute is set to
        something other than a number
        """
        entry = BudgetEntry(budget=self.test_budget, cost=10)
        with self.assertRaises(TypeError) as cm:
            entry.cost = 'some string'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.cost should be a number, not str'
        )

    def test_cost_argument_is_working_properly(self):
        """testing if the cost argument value is correctly passed to the cost
        attribute
        """
        entry = BudgetEntry(budget=self.test_budget, cost=10)
        self.assertEqual(entry.cost, 10.0)

    def test_cost_attribute_is_working_properly(self):
        """testing if the cost attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, cost=10)
        test_value = 5.0
        self.assertNotEqual(entry.cost, test_value)
        entry.cost = test_value
        self.assertEqual(entry.cost, test_value)

    def test_msrp_argument_is_skipped(self):
        """testing if the msrp attribute will be 0 if the msrp argument is
        skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.msrp, 0.0)

    def test_msrp_argument_is_set_to_None(self):
        """testing if the msrp attribute will be set to 0 if the msrp argument
        is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, msrp=None)
        self.assertEqual(entry.msrp, 0.0)

    def test_msrp_attribute_is_set_to_None(self):
        """testing if the msrp attribute will be set to 0 if msrp attribute is
        set to None
        """
        entry = BudgetEntry(budget=self.test_budget, msrp=10.0)
        self.assertEqual(entry.msrp, 10.0)
        entry.msrp = None
        self.assertEqual(entry.msrp, 0.0)

    def test_msrp_argument_is_not_a_number(self):
        """testing if a TypeError will be raised if the msrp argument is set to
        something other than a number
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, msrp='some string')

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.msrp should be a number, not str'
        )

    def test_msrp_attribute_is_not_a_number(self):
        """testing if a TypeError will be raised if msrp attribute is set to
        something other than a number
        """
        entry = BudgetEntry(budget=self.test_budget, msrp=10)
        with self.assertRaises(TypeError) as cm:
            entry.msrp = 'some string'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.msrp should be a number, not str'
        )

    def test_msrp_argument_is_working_properly(self):
        """testing if the msrp argument value is correctly passed to the msrp
        attribute
        """
        entry = BudgetEntry(budget=self.test_budget, msrp=10)
        self.assertEqual(entry.msrp, 10.0)

    def test_msrp_attribute_is_working_properly(self):
        """testing if the msrp attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, msrp=10)
        test_value = 5.0
        self.assertNotEqual(entry.msrp, test_value)
        entry.msrp = test_value
        self.assertEqual(entry.msrp, test_value)




    def test_price_argument_is_skipped(self):
        """testing if the price attribute will be 0 if the price argument is
        skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.price, 0.0)

    def test_price_argument_is_set_to_None(self):
        """testing if the price attribute will be set to 0 if the price
        argument is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, price=None)
        self.assertEqual(entry.price, 0.0)

    def test_price_attribute_is_set_to_None(self):
        """testing if the price attribute will be set to 0 if price attribute
        is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, price=10.0)
        self.assertEqual(entry.price, 10.0)
        entry.price = None
        self.assertEqual(entry.price, 0.0)

    def test_price_argument_is_not_a_number(self):
        """testing if a TypeError will be raised if the price argument is set
        to something other than a number
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, price='some string')

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.price should be a number, not str'
        )

    def test_price_attribute_is_not_a_number(self):
        """testing if a TypeError will be raised if price attribute is set to
        something other than a number
        """
        entry = BudgetEntry(budget=self.test_budget, price=10)
        with self.assertRaises(TypeError) as cm:
            entry.price = 'some string'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.price should be a number, not str'
        )

    def test_price_argument_is_working_properly(self):
        """testing if the price argument value is correctly passed to the price
        attribute
        """
        entry = BudgetEntry(budget=self.test_budget, price=10)
        self.assertEqual(entry.price, 10.0)

    def test_price_attribute_is_working_properly(self):
        """testing if the price attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, price=10)
        test_value = 5.0
        self.assertNotEqual(entry.price, test_value)
        entry.price = test_value
        self.assertEqual(entry.price, test_value)

    def test_realized_total_argument_is_skipped(self):
        """testing if the realized_total attribute will be 0 if the
        realized_total argument is skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.realized_total, 0.0)

    def test_realized_total_argument_is_set_to_None(self):
        """testing if the realized_total attribute will be set to 0 if the
        realized_total argument is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, realized_total=None)
        self.assertEqual(entry.realized_total, 0.0)

    def test_realized_total_attribute_is_set_to_None(self):
        """testing if the realized_total attribute will be set to 0 if it is
        set to None
        """
        entry = BudgetEntry(budget=self.test_budget, realized_total=10.0)
        self.assertEqual(entry.realized_total, 10.0)
        entry.realized_total = None
        self.assertEqual(entry.realized_total, 0.0)

    def test_realized_total_argument_is_not_a_number(self):
        """testing if a TypeError will be raised if the realized_total argument
        is set to something other than a number
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, realized_total='some string')

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.realized_total should be a number, not str'
        )

    def test_realized_total_attribute_is_not_a_number(self):
        """testing if a TypeError will be raised if realized_total attribute is
        set to something other than a number
        """
        entry = BudgetEntry(budget=self.test_budget, realized_total=10)
        with self.assertRaises(TypeError) as cm:
            entry.realized_total = 'some string'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.realized_total should be a number, not str'
        )

    def test_realized_total_argument_is_working_properly(self):
        """testing if the realized_total argument value is correctly passed to
        the realized_total attribute
        """
        entry = BudgetEntry(budget=self.test_budget, realized_total=10)
        self.assertEqual(entry.realized_total, 10.0)

    def test_realized_total_attribute_is_working_properly(self):
        """testing if the realized_total attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, realized_total=10)
        test_value = 5.0
        self.assertNotEqual(entry.realized_total, test_value)
        entry.realized_total = test_value
        self.assertEqual(entry.realized_total, test_value)

    def test_unit_argument_is_skipped(self):
        """testing if the unit attribute will be an empty string if the unit
        argument is skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.unit, '')

    def test_unit_argument_is_set_to_None(self):
        """testing if the unit attribute will be set to an empty string if the
        unit argument is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, unit=None)
        self.assertEqual(entry.unit, '')

    def test_unit_attribute_is_set_to_None(self):
        """testing if the unit attribute will be set to an empty if it is set
        to None
        """
        entry = BudgetEntry(budget=self.test_budget, unit='$/hour')
        self.assertEqual(entry.unit, '$/hour')
        entry.unit = None
        self.assertEqual(entry.unit, '')

    def test_unit_argument_is_not_a_string(self):
        """testing if a TypeError will be raised if the unit argument is set to
        something other than a string
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, unit=10.0)

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.unit should be a string, not float'
        )

    def test_unit_attribute_is_not_a_string(self):
        """testing if a TypeError will be raised if the unit attribute is set
        to something other than a string
        """
        entry = BudgetEntry(budget=self.test_budget, unit='$/hour')
        with self.assertRaises(TypeError) as cm:
            entry.unit = 100.212

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.unit should be a string, not float'
        )

    def test_unit_argument_is_working_properly(self):
        """testing if the unit argument value is correctly passed to the unit
        attribute
        """
        entry = BudgetEntry(budget=self.test_budget, unit='$/hour')
        self.assertEqual(entry.unit, '$/hour')

    def test_unit_attribute_is_working_properly(self):
        """testing if the unit attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, unit='$/hour')
        test_value = 'TL/hour'
        self.assertNotEqual(entry.unit, test_value)
        entry.unit = test_value
        self.assertEqual(entry.unit, test_value)

    def test_amount_argument_is_skipped(self):
        """testing if the amount attribute will be 0 if the amount argument is
        skipped
        """
        entry = BudgetEntry(budget=self.test_budget)
        self.assertEqual(entry.amount, 0.0)

    def test_amount_argument_is_set_to_None(self):
        """testing if the amount attribute will be set to 0 if the amount
        argument is set to None
        """
        entry = BudgetEntry(budget=self.test_budget, amount=None)
        self.assertEqual(entry.amount, 0.0)

    def test_amount_attribute_is_set_to_None(self):
        """testing if the amount attribute will be set to 0 if it is set to
        None
        """
        entry = BudgetEntry(budget=self.test_budget, amount=10.0)
        self.assertEqual(entry.amount, 10.0)
        entry.amount = None
        self.assertEqual(entry.amount, 0.0)

    def test_amount_argument_is_not_a_number(self):
        """testing if a TypeError will be raised if the amount argument is set
        to something other than a number
        """
        with self.assertRaises(TypeError) as cm:
            BudgetEntry(budget=self.test_budget, amount='some string')

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.amount should be a number, not str'
        )

    def test_amount_attribute_is_not_a_number(self):
        """testing if a TypeError will be raised if amount attribute is set to
        something other than a number
        """
        entry = BudgetEntry(budget=self.test_budget, amount=10)
        with self.assertRaises(TypeError) as cm:
            entry.amount = 'some string'

        self.assertEqual(
            str(cm.exception),
            'BudgetEntry.amount should be a number, not str'
        )

    def test_amount_argument_is_working_properly(self):
        """testing if the amount argument value is correctly passed to the
        amount attribute
        """
        entry = BudgetEntry(budget=self.test_budget, amount=10)
        self.assertEqual(entry.amount, 10.0)

    def test_amount_attribute_is_working_properly(self):
        """testing if the amount attribute is working properly
        """
        entry = BudgetEntry(budget=self.test_budget, amount=10)
        test_value = 5.0
        self.assertNotEqual(entry.amount, test_value)
        entry.amount = test_value
        self.assertEqual(entry.amount, test_value)

    def test_total_property_is_read_only(self):
        """testing if the total property is a read-only property
        """
        entry = BudgetEntry(
            budget=self.test_budget,
            cost=100.0,
            unit='$/hour',
            amount=53
        )

        with self.assertRaises(AttributeError) as cm:
            # use setattr to prevent the IDE to highlight
            # this line as a weak warning
            setattr(entry, 'total', 10002)

        self.assertEqual(
            str(cm.exception),
            "can't set attribute"
        )

    def test_total_property_is_working_properly(self):
        """testing if the total property is working properly
        """
        entry = BudgetEntry(
            budget=self.test_budget,
            cost=100.0,
            unit='$/hour',
            amount=53
        )
        self.assertEqual(
            entry.total,
            5300.0
        )


class BudgetDAGMixinTestCase(BudgetTestBase):
    """tests the parent/child relation of budgets
    """

    def test_parent_child_relation(self):
        """testing the parent/child relation of Budgets
        """
        b1 = Budget(**self.kwargs)
        b2 = Budget(**self.kwargs)

        b2.parent = b1
        self.assertEqual(b1.children, [b2])
