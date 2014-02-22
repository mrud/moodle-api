#!/usr/bin/env python
# -*- coding: utf8 -*- 
__author__ = 'uli'

import mechanize
import urlparse


class CourseNotFound(Exception):
    pass


class CourseMissing(Exception):
    pass


class ParsingError(Exception):
    pass


class Moodle(object):
    def __init__(self, base_url='https://csimoodle.ucd.ie/moodle/'):
        self.base_url = base_url
        self.browser = mechanize.Browser(factory=mechanize.RobustFactory())
        self._course = None
        self._course_id = None

    def _select_form_by_id(self, name):
        number = 0
        for offset, form in enumerate(self.browser.forms()):
            if form.attrs["id"] != name:
                continue
            number = offset
            break

        else:
            raise ParsingError

        self.browser.select_form(nr=number)

    def login(self, user, password):
        self.browser.open("{0}/login/".format(self.base_url))

        self._select_form_by_id(u"login")

        self.browser["username"] = user
        self.browser["password"] = password
        self.browser.submit()

    @property
    def course(self):
        return self._course

    @course.setter
    def course(self, course):
        self._course = course
        self.browser.open("{0}".format(self.base_url))

        links = list(self.browser.links(text_regex=course))
        if not links:
            raise CourseNotFound
        l = links[0]
        self._course_id = urlparse.parse_qs(urlparse.urlparse(l.url).query)["id"][0]
        self._course_url = l.url

    def check_questions(self, category=None, func=None):
        if not self._course_id:
            raise CourseMissing

        self.browser.open("{0}/question/edit.php?courseid={1}".format(self.base_url, self._course_id))
        if category:
            self._select_form_by_id(u"catmenu")
            categories = self.browser.form.find_control("category")
            for cat in categories.items:
                text = unicode([label.text for label in cat.get_labels()])
                if category in text:
                    self.browser["category"] = [cat.name]
                    self.browser.submit()
                    break
            else:
                raise ParsingError

        for link in list(self.browser.links(url_regex="{0}question/question.php".format(self.base_url))):
            if dict(link.attrs)["title"] != u"Edit":
                continue

            self.browser.follow_link(link)
            if func:
                func(self)
