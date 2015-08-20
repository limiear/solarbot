import unittest
import abstract
import datetime
from solarbot import bot


class TestSolarbot(abstract.TestCase):

    def test_measure_time_elapsed(self):
        start = datetime.datetime.now()
        self.bot = bot.run()
        end = datetime.datetime.now()
        elapsed = (end - start).total_seconds()
        self.assertGreater(elapsed, 50)


if __name__ == '__main__':
    unittest.main()
