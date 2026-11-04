/**
 * UI smoke only: intercepts backend calls with fixtures inside an isolated Playwright context.
 * No fixture login or fake data is included in the shipped application.
 * This checks rendering/interactions, NOT real authentication, permissions or MySQL.
 * Usage: set FORUM_PLAYWRIGHT_MODULE to an available playwright module, start Vite, run node this-file.
 */
const { chromium } = require(process.env.FORUM_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true,
    executablePath: process.env.FORUM_BROWSER_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  const output = process.env.FORUM_TEST_OUTPUT || path.join(__dirname, 'artifacts');
  fs.mkdirSync(output, { recursive: true });
  const outcomes = [];
  try {
    for (const operator of [false, true]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
      const comments = [{ commentId: 11, topicId: 1, authorId: 100, authorName: '普通成员', content: '建议支持按阀井编号查询', createTime: '2026-10-26 20:00:00' }];
      const replies = [];
      const errors = [];
      const permissions = ['forum:topic:query', 'forum:comment:list', 'forum:comment:add', ...(operator ? ['forum:reply:add', 'forum:comment:edit', 'forum:comment:remove', 'forum:reply:edit', 'forum:reply:remove'] : [])];
      let posted = null;
      await context.route('**/dev-api/**', async route => {
        const req = route.request();
        const url = new URL(req.url());
        const endpoint = url.pathname.replace('/dev-api', '');
        let data = { code: 200, data: [] };
        if (endpoint === '/captchaImage') data = { code: 200, captchaEnabled: false };
        else if (endpoint === '/login') data = { code: 200, token: 'fixture-only-token' };
        else if (endpoint === '/getInfo') data = { code: 200, user: { userId: operator ? 101 : 100, userName: operator ? 'forum_operator' : 'forum_member', nickName: operator ? '业务维护人员' : '普通成员', avatar: '' }, roles: [operator ? 'forum_operator' : 'forum_member'], permissions, isDefaultModifyPwd: false, isPasswordExpired: false };
        else if (endpoint === '/getRouters') data = { code: 200, data: [{ name: 'Forum', path: '/forum', component: 'Layout', redirect: '/forum/discussion', meta: { title: '反馈讨论', icon: 'message' }, children: [{ name: 'Discussion', path: 'discussion', component: 'forum/discussion/index', meta: { title: '讨论区', icon: 'message', noCache: true } }] }] };
        else if (endpoint === '/forum/topic') data = { code: 200, data: { topicId: 1, title: '阀井台账系统使用反馈', description: '请分享台账查询、现场巡检及系统使用中的建议。维护人员会在评论下回复。' } };
        else if (endpoint === '/forum/comments' && req.method() === 'GET') data = { code: 200, rows: comments, total: comments.length };
        else if (endpoint === '/forum/comments' && req.method() === 'POST') {
          posted = req.postDataJSON();
          const row = { ...posted, commentId: 12, authorName: operator ? '业务维护人员' : '普通成员', createTime: '2026-10-26 20:01:00' };
          comments.unshift(row); data = { code: 200, data: row };
        } else if (endpoint.endsWith('/replies') && req.method() === 'GET') data = { code: 200, rows: replies, total: replies.length };
        else if (endpoint === '/forum/replies' && req.method() === 'POST') {
          const row = { ...req.postDataJSON(), commentId: 20, authorId: 101, authorName: '业务维护人员', createTime: '2026-10-26 20:02:00' };
          replies.push(row); data = { code: 200, data: row };
        } else if (/^\/forum\/(comments|replies)\/\d+$/.test(endpoint)) {
          const rows = endpoint.includes('/replies/') ? replies : comments;
          const id = Number(endpoint.split('/').pop());
          const index = rows.findIndex(row => row.commentId === id);
          assert.ok(index >= 0, 'management target exists');
          if (req.method() === 'PUT') {
            rows[index].content = req.postDataJSON().content;
            data = { code: 200, data: rows[index] };
          } else if (req.method() === 'DELETE') {
            rows.splice(index, 1);
            if (rows === comments) replies.splice(0);
            data = { code: 200, msg: '操作成功' };
          }
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
      });
      const page = await context.newPage();
      page.setDefaultTimeout(120000);
      page.setDefaultNavigationTimeout(120000);
      page.on('pageerror', e => errors.push(e.message));
      await page.goto((process.env.FORUM_FRONTEND_URL || 'http://127.0.0.1:5173') + '/login?redirect=/forum/discussion');
      await page.getByPlaceholder('账号').fill(operator ? 'forum_operator' : 'forum_member');
      await page.getByPlaceholder('密码', { exact: true }).fill('fixture-password');
      await page.getByRole('button', { name: /登\s*录/ }).click();
      await page.getByRole('heading', { name: '一起把系统用得更好' }).waitFor();
      await page.getByText('建议支持按阀井编号查询', { exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: '维护人员回复', exact: true }).count(), operator ? 1 : 0);
      assert.equal(await page.getByRole('button', { name: '编辑评论', exact: true }).count(), operator ? 1 : 0);
      assert.equal(await page.getByRole('button', { name: '删除评论', exact: true }).count(), operator ? 1 : 0);
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'management buttons mobile overflow');
      await page.setViewportSize({ width: 1440, height: 1080 });
      await page.getByRole('button', { name: '发表评论', exact: true }).click();
      await page.getByText('内容不能为空', { exact: true }).waitFor();
      assert.equal(posted, null);
      if (operator) {
        await page.getByRole('button', { name: '维护人员回复', exact: true }).click();
        await page.getByRole('textbox', { name: '回复内容' }).fill('已记录，后续评估筛选功能。');
        await page.getByRole('button', { name: '提交回复', exact: true }).click();
        await page.getByText('已记录，后续评估筛选功能。', { exact: true }).waitFor();
        await page.getByRole('button', { name: '编辑我的回复', exact: true }).click();
        await page.getByRole('textbox', { name: '编辑内容', exact: true }).fill('修改后的维护回复');
        await page.getByRole('button', { name: '保存修改', exact: true }).click();
        await page.getByText('修改后的维护回复', { exact: true }).waitFor();
        assert.equal(replies[0].content, '修改后的维护回复');
        await page.getByRole('button', { name: '删除我的回复', exact: true }).click();
        await page.getByRole('button', { name: '确认删除', exact: true }).click();
        await page.getByText('暂无回复', { exact: true }).waitFor();
        assert.equal(replies.length, 0);
        await page.getByRole('button', { name: '编辑评论', exact: true }).click();
        await page.getByRole('textbox', { name: '编辑内容', exact: true }).fill('维护人员修改后的评论');
        await page.getByRole('button', { name: '保存修改', exact: true }).click();
        await page.getByText('维护人员修改后的评论', { exact: true }).waitFor();
        await page.getByRole('button', { name: '删除评论', exact: true }).click();
        await page.getByText('确认删除这条评论及其全部回复？删除后无法恢复。', { exact: true }).waitFor();
        await page.getByRole('button', { name: '确认删除', exact: true }).click();
        await page.getByText('还没有评论，来分享第一条建议吧', { exact: true }).waitFor();
        assert.equal(comments.length, 0);
      } else {
        await page.getByRole('textbox', { name: '评论内容' }).fill('  页面交互测试：建议显示巡检状态  ');
        await page.getByRole('button', { name: '发表评论', exact: true }).click();
        await page.getByText('页面交互测试：建议显示巡检状态', { exact: true }).waitFor();
        assert.deepEqual(posted, { topicId: 1, content: '页面交互测试：建议显示巡检状态' });
        await page.reload();
        await page.getByText('页面交互测试：建议显示巡检状态', { exact: true }).waitFor();
      }
      await page.screenshot({ path: path.join(output, operator ? 'forum-operator-fixture.png' : 'forum-member-fixture.png'), fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(350);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'mobile overflow');
      assert.deepEqual(errors, []);
      outcomes.push({ role: operator ? 'operator' : 'member', uiOnly: true, result: 'PASS' });
      await context.close();
    }
    console.log(JSON.stringify(outcomes, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
