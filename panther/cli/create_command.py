from pathlib import Path
from typing import Callable

from rich import print as rich_print
from rich.console import Console
from rich.progress import ProgressBar
from rich.prompt import Prompt

from panther import version
from panther.cli.template import Template, SingleFileTemplate


class CreateProject:
    # ERASE_LINE = 100 * ' '
    ERASE_LINE = '\x1b[2K'
    # REMOVE_LAST_LINE = f'\033[1A[{ERASE_LINE}'
    REMOVE_LAST_LINE = f'\x1b[1A{ERASE_LINE}'

    def __init__(self):
        self.console = Console()
        self.input_console = Console(style='bold magenta')
        self.project_name = ''
        self.base_directory = '.'
        self.database = '0'
        self.database_encryption = True
        self.authentication = False
        self.monitoring = True
        self.log_queries = True
        self.auto_reformat = False
        self.single_file = False
        self.questions = [
            {
                'field': 'project_name',
                'message': 'Project Name',
                'validation_func': lambda x: x != '',
                'error_message': "'{}' Is Not Valid, Can't Be Empty.",
            },
            {
                'field': 'base_directory',
                'message': 'Directory (default is .)',
                'validation_func': self._check_all_directories,
                'error_message': '"{}" Directory Already Exists.',
                'show_validation_error': True
            },
            {
                'field': 'single_file',
                'message': 'Do You Want To Work With Single File Structure',
                'is_boolean': True,
            },
            # {
            #     'field': 'database',
            #     'message': '    0: PantherDB\n    1: MongoDB\n    2: No Database\nChoose Your Database (default is 0)',
            #     'validation_func': lambda x: x in ['0', '1', '2'],
            #     'error_message': "Invalid Choice, '{}' not in ['0', '1', '2']",
            # },
            # {
            #     'field': 'database_encryption',
            #     'message': 'Do You Want Encryption For Your Database',
            #     'is_boolean': True,
            #     'condition': "self.database == '0'"
            # },
            # {
            #     'field': 'authentication',
            #     'message': 'Do You Want To Use JWT Authentication',
            #     'is_boolean': True,
            # },
            # {
            #     'field': 'monitoring',
            #     'message': 'Do You Want To Use Built-in Monitoring',
            #     'is_boolean': True,
            # },
            # {
            #     'field': 'log_queries',
            #     'message': 'Do You Want To Log Queries',
            #     'is_boolean': True,
            # },
            # {
            #     'field': 'auto_reformat',
            #     'message': 'Do You Want To Use Auto Reformat',
            #     'is_boolean': True,
            # },
        ]
        self.progress_len = len(self.questions)
        self.bar = ProgressBar(total=self.progress_len, width=40)

    def create(self, args: list) -> None:
        # Get Project Name
        if len(args) == 0:
            try:
                self.collect_creation_data()
            except KeyboardInterrupt:
                return self.console.print('\nKeyboardInterrupt', style='bold red')
        else:
            self.project_name = args[0]
            # Get Base Directory
            self.base_directory: str = '.'
            if len(args) > 1:
                self.base_directory = args[1]

        template = SingleFileTemplate if self.single_file else Template

        # Create Base Directory
        if self.base_directory != '.':
            Path(self.base_directory).mkdir()

        for file_name, data in template.items():
            path = f'{self.base_directory}/{file_name}'
            if isinstance(data, str):
                # Create File
                self._create_file(path=path, data=data)
            else:
                # Create Sub Directory
                Path(path).mkdir()

                # Create Files of Sub Directory
                for sub_file_name, sub_data in data.items():
                    inner_path = f'{path}/{sub_file_name}'
                    self._create_file(path=inner_path, data=sub_data)

    def _create_file(self, *, path: str, data: str):
        data = data.replace('{PROJECT_NAME}', self.project_name.lower())
        data = data.replace('{PANTHER_VERSION}', version())
        with Path(path).open('x') as file:
            file.write(data)

    def collect_creation_data(self):
        self.progress(0)

        for i, question in enumerate(self.questions):
            # Clean Question Data
            default = getattr(self, question['field'])
            is_boolean = question.get('is_boolean', False)
            clean_output = str  # Do Nothing
            if is_boolean:
                question['message'] += f' (default is {self._to_str(default)})'
                question['validation_func'] = self._is_boolean
                question['error_message'] = "Invalid Choice, '{}' not in ['y', 'n']"
                clean_output = self._to_boolean

            # Check Question Condition
            if 'condition' in question and eval(question.pop('condition')) is False:
                print(flush=True)
            # Ask Question
            else:
                setattr(self, question['field'], clean_output(self.ask(**question)))
            self.progress(i + 1)

    def ask(
            self,
            message: str,
            default: str | bool,
            error_message: str,
            validation_func: Callable,
            show_validation_error: bool = False,
    ) -> str:
        value = Prompt.ask(message, console=self.input_console).lower() or default
        while not validation_func(value):
            [print(end=self.REMOVE_LAST_LINE, flush=True) for _ in range(message.count('\n') + 1)]
            error = validation_func(value, return_error=True) if show_validation_error else value
            self.console.print(error_message.format(error), style='bold red')
            value = Prompt.ask(message, console=self.input_console).lower() or default
            print(end=self.REMOVE_LAST_LINE, flush=True)
        [print(end=self.REMOVE_LAST_LINE, flush=True) for _ in range(message.count('\n'))]
        return value

    def progress(self, step: int, /, extra_rows: int = 0):
        for i in range(extra_rows + 3 if step else 0):
            print(self.REMOVE_LAST_LINE, flush=True, end='\r')
        self.bar.update(step)

        message = 'Created Successfully' if step == self.progress_len else 'Creating Project'
        rich_print(f'[b]{message:<21}[/b]', end='', flush=True)
        rich_print(self.bar, flush=True)
        print('\n', flush=True)

    @classmethod
    def _to_boolean(cls, _input: str) -> bool:
        return _input in ['y', True]

    @classmethod
    def _is_boolean(cls, _input: str) -> bool:
        return _input in ['y', 'n', True, False]

    @classmethod
    def _to_str(cls, _input: bool) -> str:
        return 'y' if _input else 'n'

    @classmethod
    def _check_all_directories(cls, base_directory: str, return_error: bool = False) -> str | bool:
        """Return False or directory_name means that the directory exist."""
        if base_directory != '.' and Path(base_directory).is_dir():
            return base_directory if return_error else False

        for file_name, data in Template.items():
            sub_directory = f'{base_directory}/{file_name}'
            if Path(sub_directory).exists():
                return sub_directory if return_error else False

            if isinstance(data, dict):
                for sub_file_name in data:
                    file_path = f'{sub_directory}/{sub_file_name}'
                    if Path(file_path).exists():
                        return file_path if return_error else False
        return True


create = CreateProject().create
