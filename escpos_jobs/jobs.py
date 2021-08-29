import base64
from contextlib import contextmanager

from PIL import Image
from escpos.escpos import Escpos
from io import BytesIO


class PrinterState:
    """
    When sending `set`-commands to the printer, all variables not included in
    the call will be set to their default variables instead. In order to set
    just a single setting, while other settings are still non-default, we need
    to keep track of those settings and include them in the `set`-command.
    """
    font: str = 'a'
    bold: bool = False
    underline: int = 0
    double_height: bool = False
    double_width: bool = False
    custom_size: bool = False
    width: int = 0
    height: int = 0
    density: int = 0
    invert: bool = False
    smooth: bool = False
    flip: bool = False

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_kwargs(self):
        keys = ['font', 'bold', 'underline', 'double_height', 'double_width', 'custom_size', 'width', 'height',
                'density', 'invert', 'smooth', 'flip']
        return {k: getattr(self, k) for k in keys}


class PrinterStateContext:
    def __init__(self, job, **kwargs):
        self.job = job
        self._kwargs = kwargs

    def __enter__(self):
        self.was = {k: getattr(self.job.state, k) for k in self._kwargs}
        self.job.set_state(**self._kwargs)

    def __exit__(self, *exc):
        self.job.set_state(**self.was)


class Job:
    def __init__(self, printer: Escpos):
        self.printer = printer
        self.state = PrinterState()
        self.set_state()
        self.actions = self.get_actions()

    def set_state(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self.state, k, v)
        self.printer.set(**self.state.get_kwargs())

    def process(self, msg):
        action_name, args = msg.items()[0]
        action = self.actions[action_name]
        action(args)

    def wrapper(self, **kwargs):
        def inner():
            return PrinterStateContext(job=self, **kwargs)
        return inner

    def print(self, msg):
        self.process(msg)
        self.printer.cut()

    def bold(self, content: list):
        with self.wrapper(bold=True):
            for c in content:
                self.process(c)

    def center(self, content: list):
        with self.wrapper(align='center'):
            for c in content:
                self.process(c)

    def right(self, content: list):
        with self.wrapper(align='right'):
            for c in content:
                self.process(c)

    def textline(self, text):
        self.printer.textln(text)

    def b64img(self, content):
        img = img_from_b64(content)
        self.printer.image(img)

    def newline(self):
        self.printer.ln()

    def get_actions(self):
        return {
            'bold': self.bold,
        }


foo = {
    'meta': {},
    'contents': [
        {'printline': 'asdf'},
        {'image': 'asdfasd'},
        {'center': [
            {'println': 'foo'},
            {'inverted': [
                {'double_height': [
                    {'double_height': [
                        {'printline': 'asdf'},
                        {'b64img': 'adsf12f21q3123'}
                    ]}
                ]}
            ]}
        ]}
    ]
}


def img_from_b64(data):
    return Image.open(BytesIO(base64.b64decode(data)))


class JSONJob(Job):
    def __init__(self, printer: Escpos, data):
        super().__init__(printer)
        self.meta = data.pop('meta', None)
        self.contents = data.pop('contents')

    def do_print(self):
        for c in self.contents:
            pass
