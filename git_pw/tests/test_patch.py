import unittest

from click.testing import CliRunner as CLIRunner
import mock

from git_pw import patch


@mock.patch('git_pw.api.detail')
@mock.patch('git_pw.api.download')
@mock.patch('git_pw.utils.git_am')
class ApplyTestCase(unittest.TestCase):

    def test_apply(self, mock_git_am, mock_download, mock_detail):
        """Validate behavior with no arguments."""

        rsp = {'mbox': 'hello, world'}
        mock_detail.return_value = rsp
        mock_download.return_value = object()

        runner = CLIRunner()
        result = runner.invoke(patch.apply_cmd, ['123'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'], {'series': '*'})
        mock_git_am.assert_called_once_with(mock_download.return_value, ())

    def test_apply_with_series(self, mock_git_am, mock_download, mock_detail):
        """Validate behavior with a specific series."""

        rsp = {'mbox': 'hello, world'}
        mock_detail.return_value = rsp
        mock_download.return_value = object()

        runner = CLIRunner()
        result = runner.invoke(patch.apply_cmd, ['123', '--series', 3])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'], {'series': 3})
        mock_git_am.assert_called_once_with(mock_download.return_value, ())

    def test_apply_without_deps(self, mock_git_am, mock_download, mock_detail):
        """Validate behavior without using dependencies."""

        rsp = {'mbox': 'hello, world'}
        mock_detail.return_value = rsp
        mock_download.return_value = object()

        runner = CLIRunner()
        result = runner.invoke(patch.apply_cmd, ['123', '--no-deps'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'], {'series': None})
        mock_git_am.assert_called_once_with(mock_download.return_value, ())

    def test_apply_with_args(self, mock_git_am, mock_download, mock_detail):
        """Validate passthrough of arbitrary arguments to git-am."""

        rsp = {'mbox': 'hello, world'}
        mock_detail.return_value = rsp
        mock_download.return_value = object()

        runner = CLIRunner()
        result = runner.invoke(patch.apply_cmd, ['123', '--', '-3'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'], {'series': '*'})
        mock_git_am.assert_called_once_with(mock_download.return_value,
                                            ('-3',))


@mock.patch('git_pw.api.detail')
@mock.patch('git_pw.api.download')
@mock.patch('git_pw.patch.LOG')
class DownloadTestCase(unittest.TestCase):

    def test_download(self, mock_log, mock_download, mock_detail):
        """Validate standard behavior."""

        rsp = {'mbox': 'hello, world', 'diff': 'test'}
        mock_detail.return_value = rsp
        mock_download.return_value = '/tmp/abc123.patch'

        runner = CLIRunner()
        result = runner.invoke(patch.download_cmd, ['123'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'])
        assert mock_log.info.called

    def test_download_diff(self, mock_log, mock_download, mock_detail):
        """Validate behavior if downloading a diff instead of mbox."""

        rsp = {'mbox': 'hello, world', 'diff': 'test'}
        mock_detail.return_value = rsp

        runner = CLIRunner()
        result = runner.invoke(patch.download_cmd, ['123', '--diff'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_called_once_with(rsp['mbox'].replace(
            'mbox', 'raw'))
        assert mock_log.info.called

    @mock.patch('git_pw.api.get')
    def test_download_to_file(self, mock_get, mock_log, mock_download,
                              mock_detail):
        """Validate behavior if downloading to a specific file."""

        class MockResponse(object):
            @property
            def text(self):
                return b'alpha-beta'

        rsp = {'mbox': 'hello, world', 'diff': 'test'}
        mock_detail.return_value = rsp
        mock_get.return_value = MockResponse()

        runner = CLIRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(patch.download_cmd,
                                   ['123', 'test.patch'])

            assert result.exit_code == 0, result

            with open('test.patch') as output:
                assert ['alpha-beta'] == output.readlines()

        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_not_called()
        mock_get.assert_called_once_with(rsp['mbox'])
        assert mock_log.info.called

    @mock.patch('git_pw.api.get')
    def test_download_diff_to_file(self, mock_get, mock_log, mock_download,
                                   mock_detail):
        """Validate behavior if downloading a diff to a specific file."""

        rsp = {'mbox': 'hello, world', 'diff': b'test'}
        mock_detail.return_value = rsp

        runner = CLIRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(patch.download_cmd,
                                   ['123', '--diff', 'test.diff'])

            assert result.exit_code == 0, result

            with open('test.diff') as output:
                assert [rsp['diff'].decode()] == output.readlines()

        mock_detail.assert_called_once_with('patches', 123)
        mock_download.assert_not_called()
        mock_get.assert_not_called()
        assert mock_log.info.called


class ShowTestCase(unittest.TestCase):

    @staticmethod
    def _get_patch(**kwargs):
        rsp = {
            'id': 123,
            'msgid': 'hello@example.com',
            'date': '2017-01-01 00:00:00',
            'name': 'Sample patch',
            'submitter': {
                'name': 'foo',
                'email': 'foo@bar.com',
            },
            'state': 'new',
            'archived': False,
            'project': {
                'name': 'bar',
            },
            'delegate': {
                'username': 'johndoe',
            },
            'commit_ref': None,
            'series': [
                {
                    'id': 321,
                    'name': 'Sample series',
                }
            ],
        }

        rsp.update(**kwargs)

        return rsp

    @mock.patch('git_pw.api.detail')
    def test_show(self, mock_detail):
        """Validate standard behavior."""

        rsp = self._get_patch()
        mock_detail.return_value = rsp

        runner = CLIRunner()
        result = runner.invoke(patch.show_cmd, ['123'])

        assert result.exit_code == 0, result
        mock_detail.assert_called_once_with('patches', 123)


@mock.patch('git_pw.api.update')
@mock.patch.object(patch, '_show_patch')
class UpdateTestCase(unittest.TestCase):

    @staticmethod
    def _get_person(**kwargs):
        rsp = {
            'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com',
        }
        rsp.update(**kwargs)
        return rsp

    def test_update_no_arguments(self, mock_show, mock_update):
        """Validate behavior with no arguments."""

        runner = CLIRunner()
        result = runner.invoke(patch.update_cmd, ['123'])

        assert result.exit_code == 0, result
        mock_update.assert_called_once_with('patches', 123, [])
        mock_show.assert_called_once_with(mock_update.return_value)

    def test_update_with_arguments(self, mock_show, mock_update):
        """Validate behavior with all arguments except delegate."""

        runner = CLIRunner()
        result = runner.invoke(patch.update_cmd, [
            '123', '--commit-ref', '3ed8fb12', '--state', 'new',
            '--archived', '1'])

        assert result.exit_code == 0, result
        mock_update.assert_called_once_with('patches', 123, [
            ('commit_ref', '3ed8fb12'), ('state', 'new'), ('archived', True)])
        mock_show.assert_called_once_with(mock_update.return_value)

    @mock.patch('git_pw.api.index')
    def test_update_with_delegate(self, mock_index, mock_show, mock_update):
        """Validate behavior with delegate argument."""

        mock_index.return_value = [self._get_person()]

        runner = CLIRunner()
        result = runner.invoke(patch.update_cmd, [
            '123', '--delegate', 'doe@example.com'])

        assert result.exit_code == 0, result
        mock_index.assert_called_once_with('users', [('q', 'doe@example.com')])
        mock_update.assert_called_once_with('patches', 123, [
            ('delegate', mock_index.return_value[0]['id'])])
        mock_show.assert_called_once_with(mock_update.return_value)


@mock.patch('git_pw.utils.echo_via_pager', new=mock.Mock)
@mock.patch('git_pw.api.version', return_value=(1, 0))
@mock.patch('git_pw.api.index')
class ListTestCase(unittest.TestCase):

    @staticmethod
    def _get_patch(**kwargs):
        return ShowTestCase._get_patch(**kwargs)

    @staticmethod
    def _get_person(**kwargs):
        rsp = {
            'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com',
        }
        rsp.update(**kwargs)
        return rsp

    @staticmethod
    def _get_users(**kwargs):
        rsp = {
            'id': 1,
            'username': 'john.doe',
        }
        rsp.update(**kwargs)
        return rsp

    def test_list(self, mock_index, mock_version):
        """Validate standard behavior."""

        rsp = [self._get_patch()]
        mock_index.return_value = rsp

        runner = CLIRunner()
        result = runner.invoke(patch.list_cmd, [])

        assert result.exit_code == 0, result
        mock_index.assert_called_once_with('patches', [
            ('state', 'under-review'), ('state', 'new'), ('q', None),
            ('archived', 'false'), ('page', None), ('per_page', None),
            ('order', '-date')])

    def test_list_with_filters(self, mock_index, mock_version):
        """Validate behavior with filters applied.

        Apply all filters, including those for pagination.
        """

        submitter_rsp = [self._get_person()]
        delegate_rsp = [self._get_person()]
        patch_rsp = [self._get_patch()]
        mock_index.side_effect = [submitter_rsp, delegate_rsp, patch_rsp]

        runner = CLIRunner()
        result = runner.invoke(patch.list_cmd, [
            '--state', 'new', '--submitter', 'john@example.com',
            '--delegate', 'doe@example.com', '--archived',
            '--limit', 1, '--page', 1, '--sort', '-name', 'test'])

        assert result.exit_code == 0, result
        calls = [
            mock.call('people', [('q', 'john@example.com')]),
            mock.call('users', [('q', 'doe@example.com')]),
            mock.call('patches', [
                ('state', 'new'), ('submitter', 1), ('delegate', 1),
                ('q', 'test'), ('archived', 'true'), ('page', 1),
                ('per_page', 1), ('order', '-name')])]

        mock_index.assert_has_calls(calls)

    @mock.patch('git_pw.patch.LOG')
    def test_list_with_invalid_filters(self, mock_log, mock_index,
                                       mock_version):
        """Validate behavior with filters applied.

        Try to filter against a sumbmitter filter that's too broad. This should
        error out saying that too many possible submitters were found.
        """

        people_rsp = [self._get_person(), self._get_person()]
        patch_rsp = [self._get_patch()]
        mock_index.side_effect = [people_rsp, patch_rsp]

        runner = CLIRunner()
        result = runner.invoke(patch.list_cmd, ['--submitter',
                                                'john@example.com'])

        assert result.exit_code == 1, result
        assert mock_log.error.called

        mock_index.side_effect = [people_rsp, patch_rsp]