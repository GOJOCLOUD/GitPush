#!/usr/bin/env python3


class GitPushError(Exception):
    """所有 GitPush 错误的基类"""
    pass


class TokenError(GitPushError):
    """Token 相关错误"""
    pass


class BranchError(GitPushError):
    """分支相关错误"""
    pass


class FileSelectError(GitPushError):
    """文件选择相关错误"""
    pass


class GitCommandError(GitPushError):
    """Git 命令执行错误"""
    pass


class GitHubAPIError(GitPushError):
    """GitHub API 调用错误"""
    pass


class WorkspaceError(GitPushError):
    """工作区相关错误"""
    pass


class ConfigError(GitPushError):
    """配置相关错误"""
    pass
