import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
from easy_pil import Editor, Canvas, Font, load_image
import json
import os
import io

# --- SERVIDOR WEB FLASK (Para manter o bot acordado 24h no Render) ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot do Discord está online e funcionando 24h!"

def run():
    # O Render atribui uma porta automaticamente, mas usamos a 8080 como padrão interno
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -------------------------------------------------------------------

TOKEN = "MTU2NDAxNDk0NzMxMzM4OTYzMA.GrzLeJ.PjSVbC5R5QKWFoI3hbdPn2Mswjuz-5QLnOXBb8"

intents = discord.Intents.default()
intents.members = True  # OBRIGATÓRIO: Habilite Server Members Intent no Portal do Desenvolvedor
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra (/).")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# --- COMANDO /cria_invite ---
@bot.tree.command(name="cria_invite", description="Configura o sistema de boas-vindas do servidor.")
@app_commands.describe(
    canal="Canal onde a mensagem/imagem de invite será enviada",
    mostrar_foto="Se deseja exibir a foto de perfil do novo membro na imagem",
    mostrar_nome="Se deseja exibir o nome do novo membro na imagem",
    mensagem="Mensagem de texto a ser enviada junto com a imagem (Use {membro} para mencionar)"
)
@app_commands.checks.has_permissions(administrator=True)
async def cria_invite(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    mostrar_foto: bool,
    mostrar_nome: bool,
    mensagem: str
):
    configs = load_config()
    guild_id = str(interaction.guild_id)

    configs[guild_id] = {
        "canal_id": canal.id,
        "mostrar_foto": mostrar_foto,
        "mostrar_nome": mostrar_nome,
        "mensagem": mensagem
    }

    save_config(configs)

    await interaction.response.send_message(
        f"✅ **Sistema de boas-vindas/invite configurado com sucesso!**\n"
        f"📍 **Canal:** {canal.mention}\n"
        f"🖼️ **Mostrar foto:** {'Sim' if mostrar_foto else 'Não'}\n"
        f"🏷️ **Mostrar nome:** {'Sim' if mostrar_nome else 'Não'}\n"
        f"💬 **Mensagem:** {mensagem}",
        ephemeral=True
    )

# --- COMANDO /edita_invite ---
@bot.tree.command(name="edita_invite", description="Edita as configurações do invite/boas-vindas já criado.")
@app_commands.describe(
    canal="Novo canal (deixe em branco para não alterar)",
    mostrar_foto="Exibir a foto de perfil do membro?",
    mostrar_nome="Exibir o nome do membro?",
    mensagem="Nova mensagem de boas-vindas"
)
@app_commands.checks.has_permissions(administrator=True)
async def edita_invite(
    interaction: discord.Interaction,
    canal: discord.TextChannel = None,
    mostrar_foto: bool = None,
    mostrar_nome: bool = None,
    mensagem: str = None
):
    configs = load_config()
    guild_id = str(interaction.guild_id)

    if guild_id not in configs:
        await interaction.response.send_message(
            "❌ Nenhuma configuração encontrada para este servidor! Use `/cria_invite` primeiro.",
            ephemeral=True
        )
        return

    conf = configs[guild_id]

    if canal is not None:
        conf["canal_id"] = canal.id
    if mostrar_foto is not None:
        conf["mostrar_foto"] = mostrar_foto
    if mostrar_nome is not None:
        conf["mostrar_nome"] = mostrar_nome
    if mensagem is not None:
        conf["mensagem"] = mensagem

    configs[guild_id] = conf
    save_config(configs)

    canal_obj = interaction.guild.get_channel(conf["canal_id"])
    canal_nome = canal_obj.mention if canal_obj else "Desconhecido"

    await interaction.response.send_message(
        f"✏️ **Configurações atualizadas com sucesso!**\n"
        f"📍 **Canal:** {canal_nome}\n"
        f"🖼️ **Mostrar foto:** {'Sim' if conf['mostrar_foto'] else 'Não'}\n"
        f"🏷️ **Mostrar nome:** {'Sim' if conf['mostrar_nome'] else 'Não'}\n"
        f"💬 **Mensagem:** {conf['mensagem']}",
        ephemeral=True
    )

# --- EVENTO QUANDO ALGUÉM ENTRA NO SERVIDOR ---
@bot.event
async def on_member_join(member: discord.Member):
    configs = load_config()
    guild_id = str(member.guild.id)

    if guild_id not in configs:
        return

    conf = configs[guild_id]
    canal = member.guild.get_channel(conf["canal_id"])

    if not canal:
        return

    # Criando a imagem com Easy-PIL (Canvas 800x300)
    background = Editor(Canvas((800, 300), color="#23272A"))

    # Desenhar a foto se configurado
    if conf.get("mostrar_foto", True):
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        avatar_image = load_image(str(avatar_url))
        profile = Editor(avatar_image).resize((150, 150)).circle_image()
        background.paste(profile, (325, 40))

    # Desenhar o nome se configurado
    if conf.get("mostrar_nome", True):
        pos_y = 210 if conf.get("mostrar_foto", True) else 130
        font = Font.load_default()
        background.text((400, pos_y), f"BEM-VINDO(A), {member.display_name.upper()}!", color="white", font=font, align="center")

    # Converter imagem para bytes para enviar no Discord
    file_bytes = io.BytesIO()
    background.save(file_bytes, format="PNG")
    file_bytes.seek(0)
    discord_file = discord.File(fp=file_bytes, filename="welcome.png")

    # Formatar mensagem personalizável
    msg_texto = conf.get("mensagem", "Seja bem-vindo(a)!").replace("{membro}", member.mention)

    await canal.send(content=msg_texto, file=discord_file)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    # Inicia o servidor web Flask em segundo plano para o Render
    keep_alive()
    # Inicia o bot do Discord
    bot.run(TOKEN)
