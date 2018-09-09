from django.test import TestCase
from chatterbot.storage import DjangoStorageAdapter
from chatterbot.ext.django_chatterbot.models import Statement as StatementModel


class DjangoAdapterTestCase(TestCase):

    def setUp(self):
        """
        Instantiate the adapter.
        """
        self.adapter = DjangoStorageAdapter()

    def tearDown(self):
        """
        Remove the test database.
        """
        self.adapter.drop()


class DjangoStorageAdapterTestCase(DjangoAdapterTestCase):

    def test_count_returns_zero(self):
        """
        The count method should return a value of 0
        when nothing has been saved to the database.
        """
        self.assertEqual(self.adapter.count(), 0)

    def test_count_returns_value(self):
        """
        The count method should return a value of 1
        when one item has been saved to the database.
        """
        self.adapter.create(text="Test statement")
        self.assertEqual(self.adapter.count(), 1)

    def test_filter_statement_not_found(self):
        """
        Test that None is returned by the find method
        when a matching statement is not found.
        """
        self.assertEqual(self.adapter.filter(text="Non-existant").count(), 0)

    def test_filter_statement_found(self):
        """
        Test that a matching statement is returned
        when it exists in the database.
        """
        statement = StatementModel.objects.create(text="New statement")

        results = self.adapter.filter(text="New statement")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().text, statement.text)

    def test_update_adds_new_statement(self):
        # TODO: This should use the update method
        statement = StatementModel.objects.create(text="New statement")

        results = self.adapter.filter(text="New statement")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().text, statement.text)

    def test_update_modifies_existing_statement(self):
        statement = StatementModel.objects.create(text="New statement")
        other_statement = StatementModel.objects.create(text="New response")

        # Check the initial values
        results = self.adapter.filter(text=statement.text)
        self.assertEqual(results.first().in_response_to, None)

        statement.in_response_to = other_statement.text

        # Update the statement value
        self.adapter.update(statement)

        # Check that the values have changed
        results = self.adapter.filter(text=statement.text)
        self.assertEqual(results.first().in_response_to, other_statement.text)

    def test_get_random_returns_statement(self):
        statement = StatementModel.objects.create(text="New statement")

        random_statement = self.adapter.get_random()
        self.assertEqual(random_statement.text, statement.text)

    def test_filter_by_text_multiple_results(self):
        StatementModel.objects.create(
            text="Do you like this?",
            in_response_to="Yes"
        )
        StatementModel.objects.create(
            text="Do you like this?",
            in_response_to="No"
        )

        results = self.adapter.filter(text="Do you like this?")

        self.assertEqual(results.count(), 2)

    def test_remove(self):
        text = "Sometimes you have to run before you can walk."
        statement = self.adapter.create(text=text)

        self.adapter.remove(statement.text)
        results = self.adapter.filter(text=text)

        self.assertEqual(results.count(), 0)

    def test_remove_response(self):
        text = "Sometimes you have to run before you can walk."
        statement = StatementModel.objects.create(text=text)
        self.adapter.remove(statement.text)
        results = self.adapter.filter(text=text)

        self.assertEqual(results.count(), 0)

    def test_get_response_statements(self):
        """
        Test that we are able to get a list of only statements
        that are known to be in response to another statement.
        """
        s1 = StatementModel(text="What... is your quest?")
        s2 = StatementModel(text="This is a phone.")
        s3 = StatementModel(text="A what?", in_response_to=s2.text)
        s4 = StatementModel(text="A phone.", in_response_to=s3.text)

        for statement in [s1, s2, s3, s4]:
            self.adapter.update(statement)

        responses = self.adapter.get_response_statements()

        self.assertEqual(len(responses), 2)
        self.assertTrue(responses.filter(text="This is a phone.").exists())
        self.assertTrue(responses.filter(text="A what?").exists())


class DjangoAdapterFilterTestCase(DjangoAdapterTestCase):

    def setUp(self):
        super(DjangoAdapterFilterTestCase, self).setUp()

        self.statement1 = StatementModel(
            text="Testing...",
            in_response_to="Why are you counting?"
        )

        self.statement2 = StatementModel(
            text="Testing one, two, three.",
            in_response_to=self.statement1.text
        )

    def test_filter_text_no_matches(self):
        self.adapter.update(self.statement1)
        results = self.adapter.filter(text="Howdy")

        self.assertEqual(len(results), 0)

    def test_filter_in_response_to_no_matches(self):
        self.adapter.update(self.statement1)

        results = self.adapter.filter(in_response_to="Maybe")
        self.assertEqual(len(results), 0)

    def test_filter_equal_results(self):
        statement1 = StatementModel(text="Testing...")
        statement2 = StatementModel(text="Testing one, two, three.")

        self.adapter.update(statement1)
        self.adapter.update(statement2)

        results = self.adapter.filter(in_response_to=None)

        self.assertEqual(results.count(), 2)
        self.assertTrue(results.filter(text=statement1.text).exists())
        self.assertTrue(results.filter(text=statement2.text).exists())

    def test_filter_contains_result(self):
        self.adapter.update(self.statement1)
        self.adapter.update(self.statement2)

        results = self.adapter.filter(
            in_response_to="Why are you counting?"
        )
        self.assertEqual(results.count(), 1)
        self.assertTrue(results.filter(text=self.statement1.text).exists())

    def test_filter_contains_no_result(self):
        self.adapter.update(self.statement1)

        results = self.adapter.filter(
            in_response_to="How do you do?"
        )
        self.assertEqual(results.count(), 0)

    def test_filter_no_parameters(self):
        """
        If no parameters are passed to the filter,
        then all statements should be returned.
        """
        self.adapter.create(text="Testing...")
        self.adapter.create(text="Testing one, two, three.")

        results = self.adapter.filter()

        self.assertEqual(len(results), 2)

    def test_confidence(self):
        """
        Test that the confidence value is not saved to the database.
        The confidence attribute on statements is intended to just hold
        the confidence of the statement when it returned as a response to
        some input. Because of that, the value of the confidence score
        should never be stored in the database with the statement.
        """
        statement = StatementModel(text='Test statement')
        statement.confidence = 0.5
        statement.save()

        statement_updated = StatementModel.objects.get(pk=statement.id)

        self.assertEqual(statement_updated.confidence, 0)


class DjangoOrderingTestCase(DjangoStorageAdapterTestCase):
    """
    Test cases for the ordering of sets of statements.
    """

    def test_order_by_text(self):
        statement_a = StatementModel.objects.create(text='A is the first letter of the alphabet.')
        statement_b = StatementModel.objects.create(text='B is the second letter of the alphabet.')

        results = self.adapter.filter(order_by=['text'])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], statement_a)
        self.assertEqual(results[1], statement_b)

    def test_reverse_order_by_text(self):
        statement_a = StatementModel.objects.create(text='A is the first letter of the alphabet.')
        statement_b = StatementModel.objects.create(text='B is the second letter of the alphabet.')

        results = self.adapter.filter(order_by=['-text'])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[1], statement_a)
        self.assertEqual(results[0], statement_b)
