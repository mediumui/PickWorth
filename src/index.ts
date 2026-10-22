export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // apex 域名 301 重定向到 www（规范统一为 https://www.pickworth.top）
    if (url.hostname === "pickworth.top") {
      url.hostname = "www.pickworth.top";
      return Response.redirect(url.toString(), 301);
    }
    // 其他请求正常返回静态资源
    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
