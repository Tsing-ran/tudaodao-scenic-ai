App({
  globalData: {
    // 状态栏 / 胶囊按钮信息（自定义导航栏布局用）
    statusBarHeight: 20,
    navBarHeight: 44,
    menuRight: 10,
    safeBottom: 0,
    // 本次会话业务 ID（RAG 历史/行程游记按它聚合）
    sessionId: 'mp_' + Date.now().toString(36),
  },

  onLaunch() {
    try {
      const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const menu = wx.getMenuButtonBoundingClientRect && wx.getMenuButtonBoundingClientRect();
      const statusBarHeight = win.statusBarHeight || 20;
      this.globalData.statusBarHeight = statusBarHeight;
      this.globalData.safeBottom = (win.safeArea && (win.screenHeight - win.safeArea.bottom)) || 0;
      if (menu && menu.height) {
        // 导航栏高度 = 胶囊上下边距对称 + 胶囊高度
        this.globalData.navBarHeight = (menu.top - statusBarHeight) * 2 + menu.height;
        this.globalData.menuRight = win.screenWidth - menu.right;
      }
    } catch (e) {
      // 取不到就用默认值，不影响主流程
    }
  },
});
