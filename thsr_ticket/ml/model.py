import torch
import torch.nn as nn
from torchvision.transforms import ToTensor
from PIL import Image

# Fix imports to be absolute or relative correctly
try:
    from thsr_ticket.ml.Testmodel import CNN
    from thsr_ticket.configs import model_config
except ImportError as e:
    # Fallback usually only needed if running script directly from subfolder, which shouldn't happen in this setup
    print(f"Import warning: {e}")
    from ml.Testmodel import CNN
    import configs.model_config as model_config

class CaptchaSolver:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CaptchaSolver, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        conf = model_config.load_config()
        self.conf_set = conf['conf_set']
        self.conf_len = conf['conf_len']
        self.conf_w = conf['conf_w']
        self.conf_h = conf['conf_h']
        self.alphabet = conf['alphabet']
        self.conf_mdname = conf['conf_mdname']

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cnn = CNN()
        self.cnn.to(self.device)
        self.cnn.eval()

        if torch.cuda.is_available():
            self.cnn.load_state_dict(torch.load(self.conf_mdname))
        else:
            model = torch.load(self.conf_mdname, map_location='cpu')
            self.cnn.load_state_dict(model)
        
        self.trans = ToTensor()
        print(f"Captcha model loaded on {self.device}")

    def predict(self, img: Image.Image) -> str:
        img_tensor = self.trans(img)
        img_tensor = img_tensor.view(1, 3, self.conf_w, self.conf_h).to(self.device)

        with torch.no_grad():
            output = self.cnn(img_tensor)
            output = output.view(-1, self.conf_set)
            output = nn.functional.softmax(output, dim=1)
            output = torch.argmax(output, dim=1)
            output = output.view(-1, self.conf_len)[0]

        label = ''.join([self.alphabet[i] for i in output.cpu().numpy()])
        return label
