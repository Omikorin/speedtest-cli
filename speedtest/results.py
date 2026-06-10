
import csv
from datetime import datetime
from hashlib import md5
from io import StringIO
import json
from urllib.parse import parse_qs

from speedtest.exceptions import ShareResultsConnectFailure, ShareResultsSubmitFailure
from speedtest.http import build_opener, build_request, catch_request
from speedtest.utils import to_utf8


class SpeedtestResults(object):
    """Class for holding the results of a speedtest, including:

    Download speed
    Upload speed
    Ping/Latency to test server
    Data about server that the test was run against

    Additionally this class can return a result data as a dictionary or CSV,
    as well as submit a POST of the result data to the speedtest.net API
    to get a share results image link.
    """

    def __init__(self, download=0, upload=0, ping=0, server=None, client=None,
                 opener=None, secure=False):
        self.download = download
        self.upload = upload
        self.ping = ping
        if server is None:
            self.server = {}
        else:
            self.server = server
        self.client = client or {}

        self._share = None
        self.timestamp = '%sZ' % datetime.utcnow().isoformat()
        self.bytes_received = 0
        self.bytes_sent = 0

        if opener:
            self._opener = opener
        else:
            self._opener = build_opener()

        self._secure = secure

    def __repr__(self):
        return repr(self.dict())

    def share(self):
        """POST data to the speedtest.net API to obtain a share results
        link
        """

        if self._share:
            return self._share

        download = int(round(self.download / 1000.0, 0))
        ping = int(round(self.ping, 0))
        upload = int(round(self.upload / 1000.0, 0))

        # Build the request to send results back to speedtest.net
        # We use a list instead of a dict because the API expects parameters
        # in a certain order
        api_data = [
            'recommendedserverid=%s' % self.server['id'],
            'ping=%s' % ping,
            'screenresolution=',
            'promo=',
            'download=%s' % download,
            'screendpi=',
            'upload=%s' % upload,
            'testmethod=http',
            'hash=%s' % md5(('%s-%s-%s-%s' %
                             (ping, upload, download, '297aae72'))
                            .encode()).hexdigest(),
            'touchscreen=none',
            'startmode=pingselect',
            'accuracy=1',
            'bytesreceived=%s' % self.bytes_received,
            'bytessent=%s' % self.bytes_sent,
            'serverid=%s' % self.server['id'],
        ]

        headers = {'Referer': 'http://c.speedtest.net/flash/speedtest.swf'}
        request = build_request('://www.speedtest.net/api/api.php',
                                data='&'.join(api_data).encode(),
                                headers=headers, secure=self._secure)
        f, e = catch_request(request, opener=self._opener)
        if e:
            raise ShareResultsConnectFailure(e)

        response = f.read()
        code = f.code
        f.close()

        if int(code) != 200:
            raise ShareResultsSubmitFailure('Could not submit results to '
                                            'speedtest.net')

        qsargs = parse_qs(response.decode())
        resultid = qsargs.get('resultid')
        if not resultid or len(resultid) != 1:
            raise ShareResultsSubmitFailure('Could not submit results to '
                                            'speedtest.net')

        self._share = 'http://www.speedtest.net/result/%s.png' % resultid[0]

        return self._share

    def dict(self):
        """Return dictionary of result data"""

        return {
            'download': self.download,
            'upload': self.upload,
            'ping': self.ping,
            'server': self.server,
            'timestamp': self.timestamp,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'share': self._share,
            'client': self.client,
        }

    @staticmethod
    def csv_header(delimiter=','):
        """Return CSV Headers"""

        row = ['Server ID', 'Sponsor', 'Server Name', 'Timestamp', 'Distance',
               'Ping', 'Download', 'Upload', 'Share', 'IP Address']
        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator='')
        writer.writerow([to_utf8(v) for v in row])
        return out.getvalue()

    def csv(self, delimiter=','):
        """Return data in CSV format"""

        data = self.dict()
        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator='')
        row = [data['server']['id'], data['server']['sponsor'],
               data['server']['name'], data['timestamp'],
               data['server']['d'], data['ping'], data['download'],
               data['upload'], self._share or '', self.client['ip']]
        writer.writerow([to_utf8(v) for v in row])
        return out.getvalue()

    def json(self, pretty=False):
        """Return data in JSON format"""

        kwargs = {}
        if pretty:
            kwargs.update({
                'indent': 4,
                'sort_keys': True
            })
        return json.dumps(self.dict(), **kwargs)

