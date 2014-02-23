#!/usr/bin/env python
# -*- coding: utf8 -*-
import ConfigParser
import os

__author__ = 'uli'


from moodle import Moodle

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Verify moodle questions')
    parser.add_argument('--course', dest="course", default="COMP10060")
    parser.add_argument('--user', dest='user', help="Username used to connect to moodle")
    parser.add_argument('--password', dest='password', help="Password to use to connect")
    parser.add_argument('--config', dest='config', help='config file to load', default='moodle.cfg')
    parser.add_argument('--url', dest='url', help='moodle base url', default='https://csimoodle.ucd.ie/moodle/')

    parser.add_argument('quiz', help="The category to check", default='TEST 1')
    args = parser.parse_args()


    config = ConfigParser.ConfigParser()
    config.read([args.config, os.path.expanduser('~/.moodleapi.cfg')])

    username = config.get("account", "user")
    password = config.get("account", "pass")
    course = args.course

    if args.user:
        username = parser.user
    if args.password:
        password = args.password

    m = Moodle(args.url)
    m.login(username, password)
    m.course = course
    result = m.extract_quiz(args.quiz)
    with open("overview.csv", "w") as f:
        f.write("duration,points\n")
        for r in result:
            f.write("{0},{1}\n".format(r["duration"].total_seconds(), r["total_points"]))

    for i in [0, 1]:
        with open("q.csv".format(i+1), "w") as f:
            f.write("duration,tries,points\n")
            for r in result:
                f.write("{0},{1},{2}\n".format(r["duration"].total_seconds(), r["questions"][i]["tries"], r["questions"][i]["points"]))
