"""
This piece of code is modified from MongoEngine/flask-mongoengine
(https://github.com/MongoEngine/flask-mongoengine/blob/master/flask_mongoengine/pagination.py),
a library I originally used in this project.


LICENSE (https://github.com/MongoEngine/flask-mongoengine/blob/master/LICENSE):

Copyright (c) 2010-2016 See AUTHORS.

Some rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above
  copyright notice, this list of conditions and the following
  disclaimer in the documentation and/or other materials provided
  with the distribution.

* The names of the contributors may not be used to endorse or
  promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import math
from typing import List, Generator, Optional

from quart import abort


class Pagination:
    def __init__(self, items: List, page: int, per_page: int, total: int) -> None:
        if not items and page != 1:
            abort(404)

        self.page = page
        self.per_page = per_page
        self.total = total

    @property
    def pages(self) -> int:
        """The total number of pages"""
        return math.ceil(self.total / self.per_page)

    def iter_pages(
            self, left_edge: int = 2, left_current: int = 2, right_current: int = 5, right_edge: int = 2
    ) -> Generator[Optional[int], None, None]:
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:
        .. sourcecode:: html+jinja
            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (
                    num <= left_edge
                    or num > self.pages - right_edge
                    or self.page - left_current <= num <= self.page + right_current
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
        if last != self.pages:
            yield None
