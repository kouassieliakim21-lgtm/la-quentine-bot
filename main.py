import discord
from discord.ext import commands
import json
import os
import random

# --- CONFIGURATION INITIALE ---
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.reactions = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)

DATA_FILE = "quentine_data.json"

# --- GESTION DE LA BASE DE DONNÉES JSON ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "pourboires": 100, # Capital de départ en 🪙
            "main_zooba": "Non défini",
            "brigade": "Aucune",
            "victoires_duels": 0,
            "etoiles_michelin": [],
            "trophees_debut_saison": 0,
            "trophees_actuels": 0
        }
        save_data(data)
    return data[uid]

def update_user_data(user_id, key, value):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        get_user_data(user_id)
        data = load_data()
    data[uid][key] = value
    save_data(data)

@bot.event
async def on_ready():
    print(f"Le chef {bot.user.name} est en cuisine et prêt à servir !")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes Slash synchronisées : {len(synced)}")
    except Exception as e:
        print(e)

# --- 1. CHOIX DE LA BRIGADE (Menu Déroulant) ---
class BrigadeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="La Brigade des Viandes 🥩", description="Les Tanks (Bruce, Duke, Buck...) - Frontlane", value="La Brigade des Viandes 🥩"),
            discord.SelectOption(label="Les Chefs Poissonniers 🐟", description="Les DPS / Assassins (Nix, Jade, Steve...)", value="Les Chefs Poissonniers 🐟"),
            discord.SelectOption(label="Les Maîtres Sauciers 🧪", description="Les Supports (Fuzzy, Larry, Pepper...)", value="Les Maîtres Sauciers 🧪")
        ]
        super().__init__(placeholder="Choisissez votre spécialité en cuisine...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        update_user_data(interaction.user.id, "brigade", self.values[0])
        await interaction.response.send_message(f"👨‍🍳 Votre poste a été assigné avec succès : **{self.values[0]}** !", ephemeral=True)

class BrigadeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BrigadeSelect())

@bot.tree.command(name="quentine_choix_brigade", description="Affiche le menu de sélection de votre brigade.")
async def quentine_choix_brigade(interaction: discord.Interaction):
    view = BrigadeView()
    embed = discord.Embed(
        title="🍽️ Choix de votre Brigade - La Quentine",
        description="Sélectionnez votre rôle principal dans le restaurant via le menu ci-dessous pour intégrer votre brigade !",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- 2. COMMANDE DE PROFIL ---
@bot.tree.command(name="quentine_carte", description="Affiche votre profil complet de cuisinier/joueur.")
async def quentine_carte(interaction: discord.Interaction, membre: discord.Member = None):
    target = membre or interaction.user
    u_data = get_user_data(target.id)

    embed = discord.Embed(title=f"📋 Carte de Cuisine - {target.display_name}", color=discord.Color.gold())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🪙 Pourboires", value=f"{u_data['pourboires']} 🪙", inline=True)
    embed.add_field(name="🛡️ Brigade", value=u_data['brigade'], inline=True)
    embed.add_field(name="🐾 Animal Main", value=u_data['main_zooba'], inline=True)
    embed.add_field(name="⚔️ Duels Gagnés", value=str(u_data['victoires_duels']), inline=True)
    
    badges = ", ".join(u_data['etoiles_michelin']) if u_data['etoiles_michelin'] else "Aucune étoile pour l'instant"
    embed.add_field(name="⭐ Étoiles Michelin & Badges", value=badges, inline=False)

    await interaction.response.send_message(embed=embed)


# --- 3. SYSTÈME DE DUEL CULINAIRE ---
LISTE_DEFIS = [
    "Le Défi Flambé : Faire un Top 1 avec Larry sans utiliser de trousse de secours.",
    "Le Défi Épicé : Faire 3 kills en zone de feu ou de gaz.",
    "Le Défi Allégé : Gagner une partie en ramassant uniquement des armes communes.",
    "Le Défi du Chef : Assommer un adversaire avec un élément du décor ou une grenade.",
    "Le Défi Tartare : Jouer un tank et encaisser plus de 3000 de dégâts sans mourir."
]

class DuelButtonView(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User, mise: int):
        super().__init__(timeout=300)
        self.challenger = challenger
        self.opponent = opponent
        self.mise = mise

    @discord.ui.button(label="J'ai fini mon plat ! 🍳", style=discord.ButtonStyle.green)
    async def finish_dish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in (self.challenger, self.opponent):
            await interaction.response.send_message("Ce n'est pas votre cuisine !", ephemeral=True)
            return

        winner = interaction.user
        loser = self.opponent if winner == self.challenger else self.challenger

        w_data = get_user_data(winner.id)
        l_data = get_user_data(loser.id)

        if l_data["pourboires"] < self.mise:
            self.mise = l_data["pourboires"]

        w_data["pourboires"] += self.mise
        l_data["pourboires"] -= self.mise
        w_data["victoires_duels"] += 1

        save_data(load_data())

        embed = discord.Embed(
            title="🏆 Service Terminé - Vainqueur du Duel !",
            description=f"Le chef **{winner.mention}** a validé sa preuve dans `#degustation-replays` et remporte la mise de **{self.mise} Pourboires 🪙** face à {loser.mention} !",
            color=discord.Color.green()
        )
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"Victoire validée ! Bien joué chef 👨‍🍳", ephemeral=True)

@bot.tree.command(name="quentine_duel", description="Défie un autre membre du clan en duel culinaire avec une mise de pourboires.")
async def quentine_duel(interaction: discord.Interaction, opponent: discord.Member, mise: int):
    if opponent == interaction.user:
        await interaction.response.send_message("Vous ne pouvez pas cuisiner contre vous-même !", ephemeral=True)
        return

    c_data = get_user_data(interaction.user.id)
    if c_data["pourboires"] < mise:
        await interaction.response.send_message("Vous n'avez pas assez de Pourboires 🪙 en caisse pour cette mise !", ephemeral=True)
        return

    defi_choisi = random.choice(LISTE_DEFIS)
    embed = discord.Embed(
        title="⚔️ Nouveau Duel Culinaires en Cuisine !",
        description=f"**{interaction.user.mention}** défie **{opponent.mention}** !\n\n**Mise en jeu :** {mise} Pourboires 🪙\n\n🎯 **COMMANDE DU CHEF (Défi) :**\n`{defi_choisi}`\n\n*Postez votre preuve dans #degustation-replays et cliquez sur le bouton dès que le plat est prêt !*",
        color=discord.Color.red()
    )
    view = DuelButtonView(interaction.user, opponent, mise)
    await interaction.response.send_message(embed=embed, view=view)


# --- 4. SYSTÈME DE RECRUTEMENT (#surveillance-hygiene) ---
class CandidatureModal(discord.ui.Modal, title="Candidature - La Quentine"):
    zooba_id = discord.ui.TextInput(label="Votre ID ou Pseudo Zooba", placeholder="Ex: Pseudo#1234", required=True)
    trophees = discord.ui.TextInput(label="Nombre de trophées actuels", placeholder="Ex: 15000", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        surveillance_channel = discord.utils.get(guild.text_channels, name="surveillance-hygiene")
        
        embed = discord.Embed(title="🕵️ Nouveau Dossier en Surveillance d'Hygiène", color=discord.Color.purple())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Candidat", value=interaction.user.mention, inline=False)
        embed.add_field(name="Pseudo Zooba", value=self.zooba_id.value, inline=True)
        embed.add_field(name="Trophées", value=self.trophees.value, inline=True)

        view = RecrutementActionView(interaction.user.id)
        if surveillance_channel:
            await surveillance_channel.send(embed=embed, view=view)
            await interaction.response.send_message("Votre candidature a bien été transmise au chef dans la réserve !", ephemeral=True)
        else:
            await interaction.response.send_message("Erreur : Le salon `#surveillance-hygiene` est introuvable par le bot.", ephemeral=True)

class RecrutementActionView(discord.ui.View):
    def __init__(self, candidate_id: int):
        super().__init__(timeout=None)
        self.candidate_id = candidate_id

    @discord.ui.button(label="Embaucher 🟢", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.candidate_id)
        if member:
            await interaction.message.edit(content=f"✅ Candidature acceptée par {interaction.user.mention}.", view=None)
            await member.send("Félicitations ! Votre candidature pour le clan **LA QUENTINE** a été acceptée en cuisine !")
        else:
            await interaction.response.send_message("Membre introuvable sur le serveur.", ephemeral=True)

    @discord.ui.button(label="Recaler 🔴", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(content=f"❌ Candidature refusée par {interaction.user.mention}.", view=None)

@bot.tree.command(name="quentine_menu_recrutement", description="[Admin] Envoie le panneau de recrutement dans le salon.")
async def quentine_menu_recrutement(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return

    class OpenModalButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Postuler à la Brigade 🍳", style=discord.ButtonStyle.blurple)
        async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(CandidatureModal())

    embed = discord.Embed(
        title="🚪 Recrutement - LA QUENTINE",
        description="Vous souhaitez intégrer notre brigade de cuisine sur Zooba ? Cliquez sur le bouton ci-dessous pour remplir votre fiche de candidature !",
        color=discord.Color.orange()
    )
    await interaction.channel.send(embed=embed, view=OpenModalButton())
    await interaction.response.send_message("Panneau de recrutement déployé !", ephemeral=True)

# Lancement du bot (Remplace le texte entre guillemets par ton token secret Discord)
bot.run("mets_ton_token_discord_ici")
