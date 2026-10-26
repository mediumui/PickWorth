export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // apex 域名 301 重定向到 www（规范统一为 https://www.pickworth.top）
    if (url.hostname === "pickworth.top") {
      url.hostname = "www.pickworth.top";
      return Response.redirect(url.toString(), 301);
    }
    // /foo/index.html → /foo/ ：清理带 index.html 的 URL，避免 Search Console
    // 把 /index.html 当成“网页会自动重定向”而不收录。规范地址始终是目录形式。
    if (url.pathname.endsWith("/index.html")) {
      url.pathname = url.pathname.slice(0, -"index.html".length);
      return Response.redirect(url.toString(), 301);
    }
    // 其他请求正常返回静态资源
    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
