#!/usr/bin/env python
# -*- coding: utf8 -*-
import ConfigParser
import os

__author__ = 'uli'

from moodle import Moodle


def verify(self):
    for offset, form in enumerate(self.browser.forms()):
        if form.attrs["id"] != 'mform1':

            continue
        question_name = form["name"]
        print "Processing {0}".format(question_name)
        for name in ["program", "regex"]:
            if not globals()["verify_{0}".format(name)](form):

                print "Error: {0} - {1}: {2}".format(question_name, name, self.browser.geturl())
                break

        for control in form.controls:
            if control and control.name and control.name.startswith("expected"):
                num = control.name.replace("expected", "")
                stdin = form["stdin{0}".format(num)]
                test_code = form["testcode{0}".format(num)]
                if stdin.strip() or test_code.strip():  # make sure either stdin or test is valid
                    for name in ["whitespace", "specialchars"]:
                        if not globals()["verify_{0}".format(name)](control):

                            print "Error: {0} - {1}: {2}".format(question_name, name, self.browser.geturl())
                            return



def verify_program(form):
    return form["coderunner_type"][0] == 'c_program'


def verify_regex(form):
    return form["grader"][0] == 'RegexGrader'


def verify_whitespace(control):
    return control.value.strip() == control.value


def verify_specialchars(control):
    return not ("[" in control.value or '(' in control.value)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Verify moodle questions')
    parser.add_argument('--course', dest="course", default="COMP10060")
    parser.add_argument('--user', dest='user', help="Username used to connect to moodle")
    parser.add_argument('--password', dest='password', help="Password to use to connect")
    parser.add_argument('--config', dest='config', help='config file to load', default='moodle.cfg')
    parser.add_argument('--url', dest='url', help='moodle base url', default='https://csimoodle.ucd.ie/moodle/')

    parser.add_argument('category', help="The category to check", default='TEST 2')
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
    m.check_questions(args.category, verify)