# Copyright (c) 2020, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Regenerate all templated documentation pages."""

import sys

import httpx
from gen_credits_data import get_data as get_credits
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

URL_PREFIX = "https://raw.githubusercontent.com/pawamoy/jinja-templates/master/"
REGEN = (("docs/credits.md", get_credits, URL_PREFIX + "credits.md"),)


def main() -> int:
    """Regenerate pages listed in global `REGEN` list.

    Returns:
        An exit code.
    """
    env = SandboxedEnvironment(undefined=StrictUndefined)
    for target, get_data, template in REGEN:
        print("Regenerating", target)
        template_data = get_data()
        template_text = httpx.get(template).text
        rendered = env.from_string(template_text).render(**template_data)
        with open(target, "w") as stream:
            stream.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
