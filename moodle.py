#!/usr/bin/env python
# -*- coding: utf8 -*-
from bs4 import BeautifulSoup
import datetime

import mechanize
import urlparse

__author__ = 'uli'


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
            if not "id" in form.attrs or form.attrs["id"] != name:
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


    def get_points(self, tag):
        res = tag.find('del')
        if res:
            res.extract()
            return float(tag.text[1:])
        else:
            return float(tag.text)


    def extract_quiz(self, quiz):
        self.browser.open("{0}".format(self._course_url))
        link = list(self.browser.links(text_regex=quiz))
        quiz_id = urlparse.parse_qs(urlparse.urlparse(link[0].url).query)["id"][0]

        report_url = "{0}/mod/quiz/report.php?id={1}&&mode=overview&pagesize=1000".format(self.base_url, quiz_id)
        self.browser.open(report_url)
        self._select_form_by_id("attemptsform")
        response = self.browser.response()
        soup = BeautifulSoup(response.read())

        def has_class_but_no_id(tag):
            return tag.name == 'tr' and tag.has_attr('id') and 'mod-quiz-report-overview-report' in tag.attrs['id'] \
                and not 'emptyrow' in tag.attrs['class']


        results = []
        for item in soup.findAll(has_class_but_no_id):
            if not len(item.contents) >= 3:
                continue

            links = item.contents[2].find_all("a")
            if not links:
                continue

            name = links[0].string
            email = item.contents[3].string
            review_link = links[1].attrs['href']
            start = datetime.datetime.strptime(item.contents[5].string, '%d %B %Y %I:%M %p')
            end = datetime.datetime.strptime(item.contents[6].string, '%d %B %Y %I:%M %p')

            total_points = self.get_points(item.contents[8])

            points = []
            current_tag = item.contents[9]
            while current_tag.next_sibling:
                current_tag = current_tag.next_sibling
                points.append(self.get_points(current_tag))

            q = self._extract_questions("{0}&showall=1".format(review_link))

            result = {}
            result["name"] = name
            result["email"] = email
            result["start"] = start
            result["end"] = end
            result["duration"] = end - start
            result["total_points"] = total_points
            result["points"] = points
            result["questions"] = q
            results.append(result)

        return results


    def _extract_questions(self, url):
        self.browser.open(url)

        response = self.browser.response()
        soup = BeautifulSoup(response.read())
        results = []
        tag = soup.find("div", id="q1")
        first = True

        while first or tag.next_sibling:
            result = {}
            if not first and tag.next_sibling:
                tag = tag.next_sibling
            else:
                first = False
            if not "id" in tag.attrs:
                continue

            result["answer"] = tag.textarea.text

            url = tag.find(text="Edit question").parent.attrs['href']
            question_id = urlparse.parse_qs(urlparse.urlparse(url).query)["id"][0]
            result["question"] = question_id

            history = tag.find("div", attrs={'class': 'history'})
            tries = int(history.find("tr", attrs={'class': 'lastrow'}).contents[1].text)
            result["tries"] = tries
            result["points"] = float(tag.find(attrs={'class': 'grade'}).string.replace("Mark ", "").split(" ")[0])

            history_answers = []
            for offset, item in enumerate(history.tbody.findAll("tr")):
                histitem = {}
                if offset == 0:
                    continue
                if not item.contents[5].string.startswith("Submit:"):
                    continue
                answer = item.contents[5].string.replace("Submit:", "", 1)
                histitem["answer"] = answer
                try:
                    histitem["points"] = self.get_points(item.contents[9])
                except ValueError:
                    histitem["points"] = 0
                histitem["time"] = datetime.datetime.strptime(item.contents[3].string, '%d/%m/%y, %H:%M')
                history_answers.append(histitem)
            result["history"] = history_answers

            results.append(result)

        return results
