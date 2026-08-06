#!/usr/bin/env python3
"""追加 P0 端点到 agent.py: activate, deactivate, config CRUD"""

with open("app/api/v1/agent.py", "r") as f:
    content = f.read()

# Append new endpoints
new_endpoints = """

# ── 启用交易员（configuring/dormant → active） ──

@router.post("/my-agents/{user_agent_id}/activate", response_model=ActivateAgentResponse)
async def activate_agent(
    user_agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """激活交易员：从 configuring 或 dormant 状态恢复为 active"""
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")
    if ua.status not in ("configuring", "dormant"):
        raise HTTPException(status_code=400, detail=f"当前状态 {ua.status} 不可激活，仅 configuring/dormant 可激活")
    ua.status = "active"
    logger.info(f"激活交易员 user_id={current_user.id} user_agent_id={user_agent_id}")
    return ActivateAgentResponse(
        user_agent_id=ua.id,
        status="active",
        message="交易员已激活，将在下一轮调度中开始工作",
    )


# ── 停用交易员（active/paused → dormant） ──

@router.post("/my-agents/{user_agent_id}/deactivate", response_model=DeactivateAgentResponse)
async def deactivate_agent(
    user_agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """停用交易员：从 active/paused 进入强制休眠（dormant），需手动 reactivate"""
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")
    if ua.status not in ("active", "paused"):
        raise HTTPException(status_code=400, detail=f"当前状态 {ua.status} 不可停用，仅 active/paused 可停用")
    ua.status = "dormant"
    logger.info(f"停用交易员 user_id={current_user.id} user_agent_id={user_agent_id}")
    return DeactivateAgentResponse(
        user_agent_id=ua.id,
        status="dormant",
        message="交易员已停用（dormant），需要时可手动激活",
    )


# ── 获取交易员配置 ──

@router.get("/my-agents/{user_agent_id}/config", response_model=AgentConfigResponse)
async def get_agent_config(
    user_agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交易员详细配置"""
    # 先校验归属
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")

    cfg_result = await db.execute(
        select(AgentConfig).where(AgentConfig.hire_id == user_agent_id)
    )
    cfg = cfg_result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    return AgentConfigResponse.model_validate(cfg)


# ── 更新交易员配置 ──

@router.patch("/my-agents/{user_agent_id}/config", response_model=AgentConfigResponse)
async def update_agent_config(
    user_agent_id: int,
    req: AgentConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新交易员配置（仅传要修改的字段）"""
    # 先校验归属
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")

    cfg_result = await db.execute(
        select(AgentConfig).where(AgentConfig.hire_id == user_agent_id)
    )
    cfg = cfg_result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 增量更新非 None 字段
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(cfg, field):
            setattr(cfg, field, value)

    await db.flush()
    await db.refresh(cfg)
    logger.info(f"配置已更新 hire_id={user_agent_id} fields={list(update_data.keys())}")
    return AgentConfigResponse.model_validate(cfg)
"""

content += new_endpoints

with open("app/api/v1/agent.py", "w") as f:
    f.write(content)
print("ENDPOINTS_OK")
