import os
import tornado.ioloop
import tornado.web
import tornado.log
import queries
import time

from jinja2 import \
  Environment, PackageLoader, select_autoescape
  
ENV = Environment(
  loader=PackageLoader('blog', 'templates'),
  autoescape=select_autoescape(['html', 'xml'])
)
login_id=os.environ.get('LOGIN_ID')


class TemplateHandler(tornado.web.RequestHandler):
    def render_template(self, tpl, context):
        template = ENV.get_template(tpl)
        self.write(template.render(**context))
    
    def initialize(self):
        self.session = queries.Session(
        'postgresql://postgres@localhost:5432/blog_db')
    
    def get(self):
        self.set_header('Cache-Control', 'private')

class MainHandler(TemplateHandler):
    def get(self):
        super().get()
        posts = self.session.query('SELECT blog.title AS blog_title, blog.slug AS blog_slug, blog.publish_date, authors.name AS author_name FROM blog INNER JOIN authors ON blog.author_id=authors.id ORDER BY blog.publish_date DESC')
        self.render_template('main.html', {'posts': posts})
        
class PageHandler(TemplateHandler):
    def get(self, slug):
        super().get()
        comments = self.session.query('''
                SELECT comment_date, blog.title AS blog_title, authors.name AS blog_author_name, blog.publish_date AS blog_publish_date, blog.contents AS blog_contents, comments.comment_author AS comment_name, comments.contents AS comment_contents FROM blog INNER JOIN authors ON blog.author_id=authors.id JOIN comments ON comments.blog_id=blog.id WHERE blog.slug = %(slug)s ORDER BY comment_date DESC;
            ''', {'slug': slug})
        if len(comments) > 0:
            self.render_template('post_page.html', {'comments': comments})    
        else:
            post = self.session.query('''
            SELECT blog.title AS blog_title, authors.name AS blog_author_name, blog.publish_date AS blog_publish_date, blog.contents AS blog_contents FROM blog 
            INNER JOIN authors ON blog.author_id=authors.id WHERE blog.slug=%(slug)s
            ''', {'slug': slug})
            self.render_template('single_page.html', {'post': post})

        
    def post(self, slug):
        new_comment = self.get_body_argument('new_comment', None)
        name = self.get_body_argument('name', None)
        ts = time.gmtime()
        fmt = '%Y-%m-%d %H:%M:%S'
        comment_time = time.strftime(fmt, ts)
        post_id = int(slug[3:])
        addComment = self.session.query('INSERT INTO comments VALUES (DEFAULT, %(comment_time)s, %(new_comment)s, %(post_id)s, %(name)s)', {'comment_time': comment_time, 'new_comment': new_comment, 'post_id': post_id, 'name': name})
        self.get(slug)
        
class ArchiveHandler(TemplateHandler):
    def get(self, category):
        super().get()
        posts = self.session.query('SELECT blog.title AS blog_title, blog.slug AS blog_slug, blog.category AS blog_category, blog.publish_date, authors.name AS author_name FROM blog INNER JOIN authors ON blog.author_id=authors.id WHERE blog.category=%(category)s ORDER BY blog.publish_date DESC', {'category': category})
        self.render_template('main.html', {'posts': posts})
        
class NewpostHandler(TemplateHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")
        
    def get(self):
        super().get()
        if not self.current_user:
            self.redirect("/login")
            return
        elif self.current_user.decode("utf-8") != login_id: 
            self.redirect("/login")
            return
        self.render_template('newpost.html', {})
            
        
    def post(self):
        new_post = self.get_body_argument('new_content', None)
        title = self.get_body_argument('title', None)
        category = self.get_body_argument('category', None)
        ts = time.gmtime()
        fmt = '%Y-%m-%d %H:%M:%S'
        slug = self.get_body_argument('slug', None)
        comment_time = time.strftime(fmt, ts)
        addPost = self.session.query('INSERT INTO blog VALUES (DEFAULT, %(comment_time)s, %(title)s, %(slug)s, %(contents)s, 1, %(category)s)', {'comment_time': comment_time, 'title': title, 'slug': slug, 'contents': new_post, 'category': category})
        
class Login(NewpostHandler):
    def get(self):
        self.render_template('login.html', {})
        
    def post(self):
        self.set_secure_cookie("user", self.get_body_argument("username", "admin"))
        self.redirect("/create_post")
        
def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/post/(.*)", PageHandler),
        (r"/list/(.*)", ArchiveHandler),
        (r"/login", Login),
        (r"/create_post", NewpostHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler,
        {'path': 'blog/static'})
        ], cookie_secret='61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=',
        autoreload=True)
        
if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    app = make_app()
    app.listen(int(os.environ.get('PORT', '8080')))
    tornado.ioloop.IOLoop.current().start()