import pytest
from galaxy.api.types import LocalGame, LocalGameState
from galaxy.proc_tools import ProcessId, ProcessInfo
from galaxy.unittest.mock import AsyncMock

_GAME_ID = "game-id"
_INSTALL_PATH = "x:/games/game-id"
_GAME_BIN_PATH = "x:/games/game-id/game.exe"
_PROCESS_LIST = [
    ProcessInfo(ProcessId(13), "c:/windows/neshta.exe")
    , ProcessInfo(ProcessId(42), "games/game-id/game.exe")
]
_PROCESS_LIST_GAME_RUNNING = [
    ProcessInfo(ProcessId(13), "c:/windows/neshta.exe")
    , ProcessInfo(ProcessId(666), _GAME_BIN_PATH)
    , ProcessInfo(ProcessId(42), "games/game-id/game.exe")
]


def _db_installed_game(asin: str, is_installed: bool, install_path: str):
    return {
        "Id": asin
        , "Installed": int(is_installed)
        , "InstallDirectory": install_path
    }


def _installed_game(game_id):
    return LocalGame(game_id, LocalGameState.Installed)


@pytest.fixture()
def process_iter_mock(mocker):
    return mocker.patch("twitch_plugin.process_iter")


@pytest.fixture()
def get_owned_games_mock(mocker):
    return mocker.patch("twitch_plugin.TwitchPlugin._get_owned_games", new=AsyncMock(return_value={}))


@pytest.mark.asyncio
@pytest.mark.parametrize("db_response, owned_games, running_processes", [
    (Exception, [], None)
    , ([], [], None)
    , (
        [
            _db_installed_game("8530321b-a8dd-4a74-baa3-24a247454c36", False, "")
            , _db_installed_game(_GAME_ID, True, _INSTALL_PATH)
        ]
        , [LocalGame(_GAME_ID, LocalGameState.Installed)]
        , _PROCESS_LIST
    )
    , (
        [_db_installed_game(_GAME_ID, True, _INSTALL_PATH)]
        , [LocalGame(_GAME_ID, LocalGameState.Installed | LocalGameState.Running)]
        , _PROCESS_LIST_GAME_RUNNING
    )
    , ([_db_installed_game(_GAME_ID, True, "")], [], None)
])
async def test_installed_games(
    db_response
    , owned_games
    , running_processes
    , installed_twitch_plugin
    , db_select_mock
    , os_path_exists_mock
    , process_iter_mock
    , get_owned_games_mock
):
    db_select_mock.side_effect = [db_response]
    process_iter_mock.side_effect = [running_processes]

    installed_twitch_plugin.handshake_complete()

    assert owned_games == await installed_twitch_plugin.get_local_games()

    db_select_mock.assert_called_once()
    if running_processes is not None:
        process_iter_mock.assert_called()


@pytest.mark.asyncio
async def test_install_game(installed_twitch_plugin, twitch_launcher_mock):
    await installed_twitch_plugin.launch_game(_GAME_ID)

    twitch_launcher_mock.launch_game.assert_called_once_with(_GAME_ID)


@pytest.mark.asyncio
async def test_launch_game(installed_twitch_plugin, twitch_launcher_mock):
    await installed_twitch_plugin.launch_game(_GAME_ID)

    twitch_launcher_mock.launch_game.assert_called_once_with(_GAME_ID)


@pytest.mark.asyncio
async def test_uninstall_game(installed_twitch_plugin, twitch_launcher_mock) -> None:
    await installed_twitch_plugin.uninstall_game(_GAME_ID)

    twitch_launcher_mock.uninstall_game.assert_called_once_with(_GAME_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("old_game_state, new_game_state, running_processes, expected_call", [
    # not installed -> not installed
    (
        _db_installed_game("game-id", False, "")
        , _db_installed_game("game-id", False, "")
        , []
        , None
    )
    , (
        _db_installed_game("game-id", False, "")
        , _db_installed_game("game-id", True, "")
        , []
        , None
    )
    , (
        _db_installed_game("game-id", False, "")
        , _db_installed_game("game-id", False, _INSTALL_PATH)
        , []
        , None
    )
    , (
        _db_installed_game("game-id", False, "")
        , None
        , []
        , None
    )
    , (
        None
        , _db_installed_game("game-id", False, "")
        , []
        , None
    )
    # not installed -> installed
    , (
        _db_installed_game("game-id", False, "")
        , _db_installed_game("game-id", True, _INSTALL_PATH)
        , []
        , LocalGame("game-id", LocalGameState.Installed)
    )
    , (
        _db_installed_game("game-id", True, "")
        , _db_installed_game("game-id", True, _INSTALL_PATH)
        , []
        , LocalGame("game-id", LocalGameState.Installed)
    )
    # installed -> installed
    , (
        _db_installed_game("game-id", True, _INSTALL_PATH)
        , _db_installed_game("game-id", True, _INSTALL_PATH)
        , []
        , None
    )
    , (
        None
        , _db_installed_game("game-id", True, _INSTALL_PATH)
        , []
        , LocalGame("game-id", LocalGameState.Installed)
    )
    # installed -> running
    , (
        None
        , _db_installed_game("game-id", True, _INSTALL_PATH)
        , _PROCESS_LIST_GAME_RUNNING
        , LocalGame("game-id", LocalGameState.Installed | LocalGameState.Running)
    )
    # running -> not installed
    , (
        _db_installed_game("game-id", True, _INSTALL_PATH)
        , _db_installed_game("game-id", False, "")
        , []
        , LocalGame("game-id", LocalGameState.None_)
    )
    # installed -> not installed
    , (
        _db_installed_game("game-id", True, _INSTALL_PATH)
        , _db_installed_game("game-id", False, "")
        , []
        , LocalGame("game-id", LocalGameState.None_)
    )
    , (
        _db_installed_game("game-id", True, _INSTALL_PATH)
        , _db_installed_game("game-id", True, "")
        , []
        , LocalGame("game-id", LocalGameState.None_)
    )
    , (
        _db_installed_game("game-id", True, _INSTALL_PATH)
        , None
        , []
        , LocalGame("game-id", LocalGameState.None_)
    )
])
async def test_local_game_update(
    old_game_state
    , new_game_state
    , running_processes
    , expected_call
    , installed_twitch_plugin
    , db_select_mock
    , process_iter_mock
    , get_owned_games_mock
    , mocker
):
    # prepare
    db_select_mock.return_value = [old_game_state]
    update_local_game_status_mock = mocker.patch("twitch_plugin.TwitchPlugin.update_local_game_status")
    process_iter_mock.side_effect = [running_processes]

    installed_twitch_plugin.handshake_complete()
    assert db_select_mock.call_count == 1

    # test
    db_select_mock.return_value = [new_game_state]
    process_iter_mock.side_effect = [running_processes]

    await installed_twitch_plugin.tick()
    assert db_select_mock.call_count == 2

    if expected_call is None:
        update_local_game_status_mock.assert_not_called()
    else:
        update_local_game_status_mock.assert_called_once_with(expected_call)
