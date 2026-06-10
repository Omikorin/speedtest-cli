import math
import sys
import threading

global DEBUG
DEBUG = False


def distance(origin, destination):
    """Determine distance between 2 sets of [lat,lon] in km"""

    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def get_attributes_by_tag_name(dom, tag_name):
    """Retrieve an attribute from an XML document and return it in a
    consistent format

    Only used with xml.dom.minidom, which is likely only to be used
    with python versions older than 2.5
    """
    elem = dom.getElementsByTagName(tag_name)[0]
    return dict(list(elem.attributes.items()))


def print_dots(shutdown_event: threading.Event):
    """Built in callback function used by Thread classes for printing
    status
    """

    def inner(current, total, start=False, end=False):
        if shutdown_event.is_set():
            return

        sys.stdout.write(".")
        if current + 1 == total and end is True:
            sys.stdout.write("\n")
        sys.stdout.flush()

    return inner


def do_nothing(*args, **kwargs):
    pass


def printer(string, quiet=False, debug=False, error=False, **kwargs):
    """Helper function print a string with various features"""

    if debug and not DEBUG:
        return

    if debug:
        if sys.stdout.isatty():
            out = "\033[1;30mDEBUG: %s\033[0m" % string
        else:
            out = "DEBUG: %s" % string
    else:
        out = string

    if error:
        kwargs["file"] = sys.stderr

    if not quiet:
        print(out, **kwargs)
