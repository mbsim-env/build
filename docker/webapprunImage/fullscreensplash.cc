#include <QtWidgets/QApplication>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QLabel>

class SplashWindow : public QMainWindow {
  public:
    SplashWindow(int argc, char *argv[]);
};

SplashWindow::SplashWindow(int argc, char *argv[]) {
  auto *label=new QLabel(tr(
    "<h2>Preparing Web-Application</h2>"
    "<p>Please wait!</p>"
    "<p>The program <code>%2</code> will launch the<br/>"
    "example <code>%3</code> when ready.</p>"
    "<p>If this is the first time the build ID <code>%1</code> is started<br/>"
    "it may take about 1 minute to install this build.</p>"
  ).arg(argv[1]).arg(argv[2]).arg(argv[3]));
  label->setContentsMargins(50,0,0,0);
  setCentralWidget(label);
}

int main(int argc, char *argv[]) {
  QApplication app(argc, argv);
  SplashWindow mainWindow(argc, argv);
  mainWindow.show();
  mainWindow.showFullScreen();
  int ret=app.exec();
  return ret;
}
