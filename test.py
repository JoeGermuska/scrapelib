#!/usr/bin/env python
import os
import time
import unittest
import scrapelib
import threading
import BaseHTTPServer
import SimpleHTTPServer


class SilentRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TestServerThread(threading.Thread):
    def __init__(self, test_object):
        super(TestServerThread, self).__init__()
        self.test_object = test_object
        self.test_object.lock.acquire()

    def run(self):
        try:
            self.server = BaseHTTPServer.HTTPServer(
                ('', 8000), SilentRequestHandler)
        finally:
            self.test_object.lock.release()

        try:
            self.server.serve_forever()
        finally:
            self.server.server_close()

    def stop(self):
        self.server.shutdown()


class ScraperTest(unittest.TestCase):
    def setUp(self):
        self.lock = threading.Lock()
        self.thread = TestServerThread(self)
        self.thread.start()
        self.lock.acquire()

    def tearDown(self):
        self.lock.release()
        self.thread.stop()

    def test_get(self):
        s = scrapelib.Scraper(requests_per_minute=0)
        self.assertEqual('this is a test.',
                         s.urlopen("http://localhost:8000/index.html"))

    def test_request_throttling(self):
        requests = 0
        s = scrapelib.Scraper(requests_per_minute=30)

        begin = time.time()
        while time.time() <= (begin + 2):
            s.urlopen("http://localhost:8000/index.html")
            requests += 1

        self.assert_(requests <= 2)

        # We should be able to make many more requests with throttling
        # disabled
        s.throttled = False
        requests = 0
        begin = time.time()
        while time.time() <= (begin + 2):
            s.urlopen("http://localhost:8000/index.html")
            requests += 1

        self.assert_(requests > 10)

    def test_follow_robots(self):
        s = scrapelib.Scraper(follow_robots=True, requests_per_minute=0)
        self.assertRaises(scrapelib.RobotExclusionError, s.urlopen,
                          "http://localhost:8000/private/secret.html")
        self.assertEqual("this is a test.",
                         s.urlopen("http://localhost:8000/index.html"))

        s.follow_robots = False
        self.assertEqual("this is a secret.", s.urlopen(
                "http://localhost:8000/private/secret.html"))

    def test_urllib2_methods(self):
        old = scrapelib.USE_HTTPLIB2
        scrapelib.USE_HTTPLIB2 = False

        s = scrapelib.Scraper(requests_per_minute=0)

        self.assertRaises(scrapelib.ScrapeError, s.urlopen,
                          "http://localhost:8000", 'HEAD')

        scrapelib.USE_HTTPLIB2 = old

if __name__ == '__main__':
    os.chdir(os.path.abspath('./test_root'))
    unittest.main()