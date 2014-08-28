import MySQLdb as mysqldb
import urwid
import sys
import time
import optparse


UPDATE_INTERVAL = 2


class ProcessInfo(urwid.WidgetWrap):

    def __init__(self, kwargs):
        for key in kwargs.iterkeys():
            if not kwargs[key]:
                kwargs[key] = 'None'

        self.id = urwid.Text(str(kwargs['Id']))
        self.user = urwid.Text(kwargs['User'])
        self.host = urwid.Text(kwargs['Host'])
        self.db = urwid.Text(kwargs['db'])
        self.time = urwid.Text(str(kwargs['Time']))
        self.cmd = urwid.Text(kwargs['Command'])
        self.state = urwid.Text(kwargs['State'])
        self.info = urwid.Text(kwargs['Info'])

        self.items = [
            ('fixed', 8, urwid.AttrMap(self.id, 'id')),
            ('fixed', 8, urwid.AttrMap(self.user, 'user')),
            ('fixed', 15, urwid.AttrMap(self.host, 'host')),
            ('fixed', 10, urwid.AttrMap(self.db, 'db')),
            ('fixed', 8, urwid.AttrMap(self.time, 'time')),
            ('fixed', 15, urwid.AttrMap(self.cmd, 'command')),
            ('fixed', 15, urwid.AttrMap(self.state, 'state')),
            ('weight', 20, urwid.AttrMap(self.info, 'info')),
        ]
        focus_map = dict.fromkeys(
            map(lambda key: key.lower(), kwargs.iterkeys()), 'focus')

        row = urwid.Columns(self.items)
        row = urwid.AttrMap(row, {}, focus_map=focus_map)

        self.__super.__init__(row)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class MyHtopModel:

    def __init__(self, kwargs):
        self.user = kwargs['user']
        self.passwd = kwargs['passwd']
        self.port = kwargs['port']
        self.host = kwargs['host']

    def connect(self):
        self.connection = mysqldb.connect(user=self.user,
                                          passwd=self.passwd,
                                          host=self.host,
                                          port=self.port)

    def get_full_process_list(self):
        lst = []
        self.connection.query('SHOW FULL PROCESSLIST')
        for row in self.connection.store_result().fetch_row(maxrows=200, how=1):
            lst.append(row)
        return lst

    def get_server_status(self):
        try:
            return self.connection.stat()
        except:
            return None


class MyHtopView:

    def __init__(self, kwargs):
        self.palette = [
            ('id', 'white', ''),
            ('user', 'yellow', ''),
            ('host', 'dark blue', ''),
            ('command', 'white', ''),
            ('db', 'yellow', ''),
            ('state', 'dark blue', ''),
            ('info', 'yellow', ''),
            ('status_header', 'white', ''),
            ('label_header', 'black', 'dark green', 'bold'),
            ('focus', 'black', 'light cyan'),
            ('body', 'dark blue', '', 'standout'), ]

        self.process_alarm = None
        self.process_lists = []
        self.model = MyHtopModel(kwargs)
        self.connect()

    def input(self, key):
        if key in ('q', 'Q'):
            self.quit()
        elif key == 'k':
            self.kill_process()

    def kill_process(self):
        try:
            (focus_widget, widget_pos) = self.listbox.get_focus()
            id = int(focus_widget.id.get_text()[0])
            self.model.connection.kill(id)
        except:
            pass

    def main(self):

        self._setup()
        self.loop = urwid.MainLoop(
            self.view, palette=self.palette, unhandled_input=self.input)
        self.process_alarm = self.loop.set_alarm_in(
            UPDATE_INTERVAL, self.update)
        self.loop.run()

    def quit(self):
        if self.process_alarm:
            self.loop.remove_alarm(self.process_alarm)
        raise urwid.ExitMainLoop()

    def _setup(self):
        self.label_header = urwid.Columns([
            ('fixed', 8, urwid.Text('Id')),
            ('fixed', 8, urwid.Text('User')),
            ('fixed', 15, urwid.Text('Host/IP')),
            ('fixed', 10, urwid.Text('DB')),
            ('fixed', 8, urwid.Text('Time')),
            ('fixed', 15, urwid.Text('Cmd')),
            ('fixed', 15, urwid.Text('State')),
            ('fixed', 15, urwid.Text('Info')),
        ])
        self.label_header = urwid.AttrMap(self.label_header, 'label_header')
        self.walker = urwid.SimpleListWalker([])
        self.set_status_header()
        self.set_body()
        self.listbox = urwid.ListBox(self.walker)
        self.view = urwid.Frame(body=urwid.AttrMap(self.listbox, 'body'),
                                header=self.label_header)

        self.view = urwid.Padding(self.view, left=2)
        self.view = urwid.Frame(
            body=self.view, header=self.status_header)

    def update(self, loop=None, data=None):
        self.set_status_header()
        self.view.set_header(self.status_header)
        self.set_body()
        loop.set_alarm_in(
            UPDATE_INTERVAL, self.update)

    def connect(self):
        self.model.connect()

    def set_status_header(self):
        txt = self.model.get_server_status()
        split = txt.split()
        split[1] = time.strftime('%H:%M:%S', time.gmtime(int(split[1])))
        split[9] = '\nOpens:'
        txt = ' '.join(split)
        self.status_header = urwid.AttrMap(urwid.Text(txt), 'status_header')
        self.status_header = urwid.Pile([self.status_header, urwid.Divider()])
        self.status_header = urwid.Padding(self.status_header, left=2)

    def set_body(self):
        self.walker[:] = []
        result = self.model.get_full_process_list()
        if result:
            for row in result:
                self.walker.append(ProcessInfo(row))


def main():
    usage = '''
         myhtop [option,]
        -h, --help      Show this message
        -p, --port      mysql port, default 3306
        -u, --user      Default root
        -p, --passwd    Default None
        -H, --host      Default localhost
    '''
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-P', '--port', dest='port', default=3306, type=int)
    parser.add_option('-u', '--user', dest='user', default='root', type=str)
    parser.add_option(
        '-p', '--passwd', dest='passwd', default='root', type=str)

    parser.add_option(
        '-H', '--host', dest='host', default='localhost', type=str)
    (option, args) = parser.parse_args()
    try:
        mainwin = MyHtopView({'user': option.user, 'passwd': option.passwd,
                              'host': option.host, 'port': option.port})
        mainwin.main()
        mainwin.model.connection.close()
    except mysqldb.Error as msg:
        print msg[1]
        sys.exit(0)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
