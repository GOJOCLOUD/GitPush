#!/usr/bin/env python3
import logging
from utils.github_api import get_branches
from errors import BranchError
from logger import log


def create_new_branch(token, repo):
    """创建新分支"""
    if not token or not isinstance(token, str):
        raise BranchError("无效的 Token 格式")
    
    if not repo or not isinstance(repo, str):
        raise BranchError("无效的仓库格式")
    
    while True:
        new_branch = input("请输入新分支名称: ").strip()
        if not new_branch:
            log("错误: 分支名称不能为空", level=logging.ERROR)
            continue
        
        # 只返回分支名，不做远端操作
        log(f"创建新分支: {new_branch}")
        return new_branch


def choose_branch(token, repo):
    """让用户选择分支"""
    if not token or not isinstance(token, str):
        raise BranchError("无效的 Token 格式")
    
    if not repo or not isinstance(repo, str):
        raise BranchError("无效的仓库格式")
    
    # 获取仓库的所有分支
    try:
        branches = get_branches(token, repo)
        if not branches:
            log("警告: 无法获取分支列表，将使用默认分支")
            return "main"
    except Exception as e:
        log(f"获取分支列表失败: {e}", level=logging.ERROR)
        raise BranchError(f"获取分支列表失败: {e}")
    
    # 打印分支列表
    log("\n可选分支列表：")
    for i, branch in enumerate(branches, 1):
        log(f"{i}. {branch}")
    
    # 添加“新建分支”选项
    log(f"{len(branches) + 1}. 新建分支")
    
    # 让用户选择分支
    while True:
        try:
            choice = input("\n请输入分支编号: ").strip()
            branch_index = int(choice) - 1
            
            if 0 <= branch_index < len(branches):
                # 选择已有分支
                selected_branch = branches[branch_index]
                log(f"选择分支: {selected_branch}")
                return selected_branch
            elif branch_index == len(branches):
                # 选择新建分支
                new_branch = create_new_branch(token, repo)
                if new_branch:
                    return new_branch
                else:
                    log("错误: 无法创建新分支", level=logging.ERROR)
                    raise BranchError("无法创建新分支")
            else:
                log(f"错误: 编号必须在 1 到 {len(branches) + 1} 之间", level=logging.ERROR)
        except ValueError:
            log("错误: 必须输入数字", level=logging.ERROR)
        except BranchError:
            raise
