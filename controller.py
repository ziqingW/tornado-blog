import os
import tornado.ioloop
import tornado.web
import tornado.log
import queries

from jinja2 import \
  Environment, PackageLoader, select_autoescape
  
ENV = Environment(
  loader=PackageLoader('blog', 'templates'),
  autoescape=select_autoescape(['html', 'xml'])
)

class TemplateHandler(tornado.web.RequestHandler):
    def render_template(self, tpl, context):
        template = ENV.get_template(tpl)
        self.write(template.render(**context))
    
    def initialize(self):
        self.session = queries.Session(
        'postgresql://postgres@localhost:5432/blog_db')
    
    def get(self):
        self.set_header('Cache-Control',
      'no-store, no-cache, must-revalidate, max-age=0')

class MainHandler(TemplateHandler):
    def get(self):
        super().get()
        posts = self.session.query('SELECT blog.title AS blog_title, blog.slug AS blog_slug, blog.publish_date, authors.name AS author_name FROM blog INNER JOIN authors ON blog.author_id=authors.id ORDER BY blog.publish_date')
        self.render_template('main.html', {'posts': posts})
        
class PageHandler(TemplateHandler):
    def get(self, slug):
        super().get()
        post = self.session.query('SELECT blog.title AS blog_title, blog.slug AS blog_slug, blog.contents, blog.publish_date, authors.name AS author_name FROM blog INNER JOIN authors ON blog.author_id=authors.id WHERE blog.slug = %(slug)s', {'slug': slug})
        self.render_template('post_page.html', {'post': post[0]})


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/post/(.*)", PageHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler,
        {'path': 'blog/static'})
        ],
        autoreload=True)
        
if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    app = make_app()
    app.listen(int(os.environ.get('PORT', '8080')))
    tornado.ioloop.IOLoop.current().start()