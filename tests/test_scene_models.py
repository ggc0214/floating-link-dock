import pytest
from floating_link_dock import scene_models as sm


def test_resources_preserve_paths_and_validate_types():
    assert sm.validate_resource(sm.ResourceDraft('url', '网站', 'example.com')).target == 'https://example.com'
    for path in [r'\\NAS\共享目录\成本 & 表.xlsx', r'Z:\资料 文件\表.xlsx']:
        assert sm.validate_resource(sm.ResourceDraft('file', '成本', path)).target == path
    with pytest.raises(ValueError, match='不支持的项目类型'):
        sm.validate_resource(sm.ResourceDraft('text', '模板', '第一行\n第二行'))


@pytest.mark.parametrize('target', [r'..\表.xlsx', r'\\?\C:\表.xlsx', r'\\.\C:\表.xlsx',
    r'C:\表.xlsx:script', 'javascript:alert(1)', r'C:\run.exe', r'C:\run.LNK', r'C:\run.bat',
    'C:\\file.xlsx\n', r'C:\x\..\run.cmd', r'\single\path.xlsx', r'C:\report.xlsx.'])
def test_reject_unsafe_file_targets(target):
    with pytest.raises(ValueError): sm.validate_resource(sm.ResourceDraft('file', '不安全', target))


def test_scene_names():
    assert sm.validate_scene_name(' 工作 ', []) == '工作'
    for name in [' ', 'WORK']:
        with pytest.raises(ValueError): sm.validate_scene_name(name, ['work'])
