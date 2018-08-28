"""
Machines
--------
"""
import abc
import typing
import pathlib
import paramiko
import tbot

KWARGS_LIST = [
    ("lab.port", "port"),
    ("lab.user", "username"),
    ("lab.password", "password"),
    ("lab.keyfile", "key_filename"),
]


class Machine(abc.ABC):
    """ Abstract base class for machines """

    def _setup(
        self,
        tb: "tbot.TBot",
        # pylint: disable=unused-argument
        previous: "typing.Optional[Machine]" = None,
    ) -> "Machine":
        self._interactive = tb.interactive
        return self

    def _destruct(self, tb: "tbot.TBot") -> None:
        pass

    @abc.abstractmethod
    def _exec(
        self, command: str, stdout_handler: typing.Optional[tbot.log.LogStdoutHandler]
    ) -> typing.Tuple[int, str]:
        pass

    @abc.abstractproperty
    def common_machine_name(self) -> str:
        """ Common name of this machine, eg ``"board"`` or ``"labhost"`` """
        pass

    @abc.abstractproperty
    def unique_machine_name(self) -> str:
        """ Unique name of this machine, eg ``"labhost-noenv"`` """
        pass

    @abc.abstractproperty
    def workdir(self) -> pathlib.PurePosixPath:
        """ Workdir where testcases can safely store data """
        pass

    def exec(
        self, command: str, log_show: bool = True, log_show_stdout: bool = True
    ) -> typing.Tuple[int, str]:
        """
        Execute a command on this machine

        :param str command: The command to be executed, no newline at the end
        :param bool log_show: Whether documentation backends should include this command
        :param bool log_show_stdout: Whether documentation backends should include the stdout
            of this command
        :returns: A tuple of the return code and the output (stdout and stderr are merged)
        :rtype: tuple[int, str]
        """
        if self._interactive:
            inp = input(f"{self.unique_machine_name!r}: {command!r} [Y/n]? ").lower()
            if inp != "" and inp[0] != "y":
                tbot.log.message(
                    f"""\
Skipping comand {command!r} ... Might cause unintended side effects!"""
                )
                return 0, ""
        stdout_handler = tbot.log_events.shell_command(
            machine=self.unique_machine_name.split("-"),
            command=command,
            show=log_show,
            show_stdout=log_show_stdout,
        )
        ret = self._exec(command, stdout_handler)
        stdout_handler.dct["exit_code"] = ret[0]
        return ret

    def exec0(self, command: str, **kwargs: bool) -> str:
        """
        Execute a command and expect it to return with 0

        :param str command: The command to be executed, no newline at the end
        :param kwargs: Passed through to Machine.exec
        :returns: The output (stdout and stderr are merged)
        :rtype: str
        """
        ret = self.exec(command, **kwargs)
        assert ret[0] == 0, f'Command "{command}" failed:\n{ret[1]}'
        return ret[1]


class MachineManager(typing.Dict[str, Machine]):
    """ A container to manage the list of available machines """

    def __init__(
        self, tb: "tbot.TBot", conn: typing.Optional[paramiko.SSHClient] = None
    ) -> None:
        if isinstance(conn, paramiko.SSHClient):
            self.connection = conn
        else:
            self.connection = paramiko.SSHClient()
            self.connection.load_system_host_keys()

            kwargs = dict(
                filter(
                    lambda arg: arg[1] is not None,
                    map(lambda arg: (arg[1], tb.config[arg[0], None]), KWARGS_LIST),
                )
            )
            # Paramiko can't handle pathlib.Path
            if "key_filename" in kwargs:
                kwargs["key_filename"] = str(kwargs["key_filename"])
            self.connection.connect(tb.config["lab.hostname"], **kwargs)

        super().__init__()