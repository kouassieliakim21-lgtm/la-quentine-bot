import discord
from discord.ext import commands
import json
import os
import random
from googletrans import Translator  # Utilisé pour la traduction automatique gratuite

# --- CONFIGURATION INITIALE ---
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.reactions = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)
translator = Translator()

DATA_FILE = "quentine_data.json"
SEASON_FILE = "quentine_season.json"

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

def load_season_data():
    if not os.path.exists(SEASON_FILE):
        return {"active": False, "start_date": None}
    with open(SEASON_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"active": False, "start_date": None}

def save_season_data(data):
    with open(SEASON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "pourboires": 100,
            "main_zooba": "Non défini",
            "brigade": "Aucune",
            "victoires_duels": 0,
            "etoiles_michelin": [],
            "trophees_debut_saison": 0,
            "trophees_actuels": 0,
            "niveau_cuisine": 1,
            "experience": 0,
            "specialite": "Aucune",
            "badges": [],
            "historique_duels": [],
            "total_gains": 0
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


# --- 0. TRADUCTION INVISIBLE AUTOMATIQUE (Réaction 🌐) ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    try:
        detected = translator.detect(message.content)
        if detected.lang != 'fr' and len(message.content) > 3:
            await message.add_reaction("🌐")
    except Exception:
        pass
        
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.emoji == "🌐":
        message = reaction.message
        try:
            translation = translator.translate(message.content, dest='fr')
            embed = discord.Embed(
                title="🌐 Traduction en Cuisine",
                description=f"**Message original ({message.author.display_name}) :**\n{message.content}\n\n**Traduction française :**\n{translation.text}",
                color=discord.Color.blue()
            )
            await user.send(embed=embed)
        except Exception:
            pass


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


# --- 2. COMMANDE DE PROFIL ENRICHI ---
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
    embed.add_field(name="⭐ Niveau Cuisine", value=f"Niveau {u_data['niveau_cuisine']} ({u_data['experience']} XP)", inline=True)
    embed.add_field(name="💰 Gains Totaux", value=f"{u_data['total_gains']} 🪙", inline=True)
    
    badges = ", ".join(u_data['etoiles_michelin']) if u_data['etoiles_michelin'] else "Aucune étoile pour l'instant"
    embed.add_field(name="⭐ Étoiles Michelin", value=badges, inline=False)
    
    badges_list = ", ".join(u_data['badges']) if u_data['badges'] else "Aucun badge"
    embed.add_field(name="🎖️ Badges & Achievements", value=badges_list, inline=False)

    await interaction.response.send_message(embed=embed)


# --- 3. SYSTÈME DE DUEL CULINAIRE AMÉLIORÉ ---
LISTE_DEFIS = [
    "Le Défi Flambé : Faire un Top 1 avec Larry sans utiliser de trousse de secours.",
    "Le Défi Épicé : Faire 3 kills en zone de feu ou de gaz.",
    "Le Défi Allégé : Gagner une partie en ramassant uniquement des armes communes.",
    "Le Défi du Chef : Assommer un adversaire avec un élément du décor ou une grenade.",
    "Le Défi Tartare : Jouer un tank et encaisser plus de 3000 de dégâts sans mourir.",
    "Le Défi Éclair : Remporter une victoire en moins de 5 minutes.",
    "Le Défi Acrobate : Faire 5 éliminations sans vous faire toucher.",
    "Le Défi Stratège : Remporter une partie sans utiliser de consommables."
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
        w_data["experience"] += 50
        w_data["total_gains"] += self.mise
        
        # Gestion du niveau
        if w_data["experience"] >= w_data["niveau_cuisine"] * 100:
            w_data["niveau_cuisine"] += 1
            w_data["badges"].append(f"🎖️ Chef Niveau {w_data['niveau_cuisine']}")

        l_data["experience"] += 20

        data = load_data()
        data[str(winner.id)] = w_data
        data[str(loser.id)] = l_data
        save_data(data)

        embed = discord.Embed(
            title="🏆 Service Terminé - Vainqueur du Duel !",
            description=f"Le chef **{winner.mention}** a validé sa preuve dans `#degustation-replays` et remporte la mise de **{self.mise} Pourboires 🪙** face à {loser.mention} !\n\n**Bonus XP :** +50 XP pour le vainqueur, +20 XP pour le perdant.",
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

    if opponent.bot:
        await interaction.response.send_message("Vous ne pouvez pas défier un bot !", ephemeral=True)
        return

    c_data = get_user_data(interaction.user.id)
    if c_data["pourboires"] < mise:
        await interaction.response.send_message("Vous n'avez pas assez de Pourboires 🪙 en caisse pour cette mise !", ephemeral=True)
        return

    if mise < 10:
        await interaction.response.send_message("La mise minimale est de 10 Pourboires 🪙 !", ephemeral=True)
        return

    defi_choisi = random.choice(LISTE_DEFIS)
    embed = discord.Embed(
        title="⚔️ Nouveau Duel Culinaires en Cuisine !",
        description=f"**{interaction.user.mention}** défie **{opponent.mention}** !\n\n**Mise en jeu :** {mise} Pourboires 🪙\n\n🎯 **COMMANDE DU CHEF (Défi) :**\n`{defi_choisi}`\n\n*Postez votre preuve dans #degustation-replays et cliquez sur le bouton dès que le plat est prêt !*",
        color=discord.Color.red()
    )
    view = DuelButtonView(interaction.user, opponent, mise)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="quentine_historique_duels", description="Affiche l'historique de vos duels.")
async def quentine_historique_duels(interaction: discord.Interaction, membre: discord.Member = None):
    target = membre or interaction.user
    u_data = get_user_data(target.id)

    embed = discord.Embed(title=f"⚔️ Historique des Duels - {target.display_name}", color=discord.Color.red())
    embed.add_field(name="Victoires Totales", value=str(u_data['victoires_duels']), inline=True)
    embed.add_field(name="Gains Totaux", value=f"{u_data['total_gains']} 🪙", inline=True)
    embed.add_field(name="Taux de Victoire Estimé", value="N/A (données détaillées à venir)", inline=True)
    
    await interaction.response.send_message(embed=embed)


# --- 4. SYSTÈME DE SPÉCIALITÉS & ANIMAUX ZOOBA ---
class SpecialiteSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bruce 🐻 - Le Tank", value="Bruce"),
            discord.SelectOption(label="Nix 🐉 - L'Assassin", value="Nix"),
            discord.SelectOption(label="Larry 🦁 - Le Support", value="Larry"),
            discord.SelectOption(label="Jade 🦗 - La DPS Magique", value="Jade"),
            discord.SelectOption(label="Steve 🦝 - Le Voleur", value="Steve"),
            discord.SelectOption(label="Duke 🐕 - Le Chevalier", value="Duke"),
            discord.SelectOption(label="Buck 🦌 - Le Ranger", value="Buck"),
            discord.SelectOption(label="Pepper 🐰 - L'Alchimiste", value="Pepper"),
            discord.SelectOption(label="Fuzzy 🐰 - L'Enchanteur", value="Fuzzy")
        ]
        super().__init__(placeholder="Choisissez votre animal principal Zooba...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        update_user_data(interaction.user.id, "main_zooba", self.values[0])
        update_user_data(interaction.user.id, "specialite", self.values[0])
        await interaction.response.send_message(f"🐾 Parfait ! **{self.values[0]}** est maintenant votre animal principal !", ephemeral=True)

class SpecialiteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpecialiteSelect())

@bot.tree.command(name="quentine_choix_specialite", description="Choisissez votre animal principal Zooba.")
async def quentine_choix_specialite(interaction: discord.Interaction):
    view = SpecialiteView()
    embed = discord.Embed(
        title="🐾 Choix de votre Animal Principal - Zooba",
        description="Sélectionnez l'animal avec lequel vous dominrez le champ de bataille !",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- 5. SYSTÈME DE SAISONS (Long Terme) ---
@bot.tree.command(name="quentine_saison_ouvrir", description="[Admin] Enregistre les trophées de départ de tous les membres pour la nouvelle saison.")
async def quentine_saison_ouvrir(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return

    data = load_data()
    season_data = load_season_data()
    
    for uid in data:
        data[uid]["trophees_debut_saison"] = data[uid]["trophees_actuels"]
    
    season_data["active"] = True
    season_data["start_date"] = str(discord.utils.utcnow())
    
    save_data(data)
    save_season_data(season_data)

    embed = discord.Embed(
        title="🗓️ Nouvelle Saison en Cuisine Ouverte !",
        description="Les compteurs sont étalonnés. Que la course aux étoiles commence pour le clan **LA QUENTINE** !\n\n⏰ La saison est active, le classement se met à jour en temps réel.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_saison_classement", description="Affiche le classement en direct basé sur la progression des trophées.")
async def quentine_saison_classement(interaction: discord.Interaction):
    data = load_data()
    season_data = load_season_data()
    
    if not season_data.get("active", False):
        await interaction.response.send_message("❌ Aucune saison active pour le moment. Un admin doit l'ouvrir avec `/quentine_saison_ouvrir`", ephemeral=True)
        return
    
    if not data:
        await interaction.response.send_message("Aucune donnée en cuisine pour l'instant.", ephemeral=True)
        return

    classement = []
    for uid, u_info in data.items():
        progression = u_info["trophees_actuels"] - u_info["trophees_debut_saison"]
        classement.append((uid, progression, u_info["trophees_actuels"], u_info.get("victoires_duels", 0)))

    classement.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="🏆 Classement de la Brigade - Saison en Cours", color=discord.Color.gold())
    
    description = ""
    for index, (uid, prog, actuels, victoires) in enumerate(classement[:15], start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"Cuisinier ID {uid}"
        medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"**#{index}**"
        description += f"{medal} **{name}** — Progression : `+{prog}` 🏆 | Duels : {victoires} ⚔️ | Total : {actuels}\n"

    embed.description = description if description else "Aucun classement disponible."
    embed.set_footer(text="Les 3 premiers seront récompensés à la fin de la saison !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_saison_cloture", description="[Admin] Clôture la saison, récompense le Top 3 et attribue le rôle Caviar 💎.")
async def quentine_saison_cloture(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return

    data = load_data()
    season_data = load_season_data()
    classement = []
    
    for uid, u_info in data.items():
        progression = u_info["trophees_actuels"] - u_info["trophees_debut_saison"]
        classement.append((uid, progression))

    classement.sort(key=lambda x: x[1], reverse=True)

    if not classement:
        await interaction.response.send_message("Personne à récompenser.", ephemeral=True)
        return

    recompenses = [5000, 3000, 1500]
    resultats_texte = "🎯 **Résultats de la Clôture de Saison :**\n\n"

    for i in range(min(3, len(classement))):
        uid, prog = classement[i]
        member = interaction.guild.get_member(int(uid))
        if member:
            prime = recompenses[i]
            data[uid]["pourboires"] += prime
            data[uid]["total_gains"] += prime
            
            if i == 0:
                data[uid]["etoiles_michelin"].append("⭐ Grand Chef de Saison")
                caviar_role = discord.utils.get(interaction.guild.roles, name="Caviar 💎")
                if caviar_role:
                    try:
                        await member.add_roles(caviar_role)
                    except:
                        pass
            elif i == 1:
                data[uid]["etoiles_michelin"].append("⭐ Sous Chef de Saison")
            else:
                data[uid]["etoiles_michelin"].append("⭐ Chef de Partie de Saison")
            
            resultats_texte += f"**Rang #{i+1}** : {member.mention}\n├─ Progression : `+{prog}` 🏆\n├─ Prime : **{prime} Pourboires 🪙**\n└─ Badge : ⭐ Étoile Michelin\n\n"

    season_data["active"] = False
    save_data(data)
    save_season_data(season_data)
    
    embed = discord.Embed(title="🛎️ Fin du Service - Clôture de Saison !", description=resultats_texte, color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)


# --- 6. SYSTÈME DE SHOP (Acheter des Items/Cosmétiques) ---
SHOP_ITEMS = {
    "1": {"nom": "Costume Chef Premium 👨‍🍳", "prix": 500, "emoji": "👨‍🍳"},
    "2": {"nom": "Auréole Dorée ✨", "prix": 300, "emoji": "✨"},
    "3": {"nom": "Trophée Miniature 🏆", "prix": 250, "emoji": "🏆"},
    "4": {"nom": "Parchemin Secret 📜", "prix": 400, "emoji": "📜"},
    "5": {"nom": "Cristal Enchanté 💎", "prix": 1000, "emoji": "💎"}
}

@bot.tree.command(name="quentine_shop", description="Accédez à la boutique pour acheter des cosmétiques.")
async def quentine_shop(interaction: discord.Interaction):
    u_data = get_user_data(interaction.user.id)
    
    embed = discord.Embed(title="🛍️ Boutique Culinaire - LA QUENTINE", color=discord.Color.purple())
    embed.add_field(name="💰 Votre Solde", value=f"{u_data['pourboires']} 🪙", inline=False)
    
    shop_text = ""
    for key, item in SHOP_ITEMS.items():
        shop_text += f"**{key}. {item['nom']}** - `{item['prix']} 🪙`\n"
    
    embed.add_field(name="📦 Articles Disponibles", value=shop_text, inline=False)
    embed.set_footer(text="Utilisez /quentine_acheter <numero> pour acheter un item")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="quentine_acheter", description="Achetez un item dans la boutique.")
async def quentine_acheter(interaction: discord.Interaction, numero: str):
    if numero not in SHOP_ITEMS:
        await interaction.response.send_message("❌ Numéro d'article invalide.", ephemeral=True)
        return
    
    item = SHOP_ITEMS[numero]
    u_data = get_user_data(interaction.user.id)
    
    if u_data["pourboires"] < item["prix"]:
        await interaction.response.send_message(f"❌ Vous n'avez pas assez de Pourboires 🪙 ! (Il vous manque {item['prix'] - u_data['pourboires']})", ephemeral=True)
        return
    
    u_data["pourboires"] -= item["prix"]
    u_data["badges"].append(item["nom"])
    update_user_data(interaction.user.id, "pourboires", u_data["pourboires"])
    update_user_data(interaction.user.id, "badges", u_data["badges"])
    
    embed = discord.Embed(
        title="✅ Achat Réussi !",
        description=f"Vous avez acheté : **{item['nom']}** {item['emoji']}\n\nSolde restant : **{u_data['pourboires']} 🪙**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 7. SYSTÈME DE RECRUTEMENT (#surveillance-hygiene) ---
class CandidatureModal(discord.ui.Modal, title="Candidature - La Quentine"):
    zooba_id = discord.ui.TextInput(label="Votre ID ou Pseudo Zooba", placeholder="Ex: Pseudo#1234", required=True)
    trophees = discord.ui.TextInput(label="Nombre de trophées actuels", placeholder="Ex: 15000", required=True)
    presentation = discord.ui.TextInput(label="Présentez-vous en une phrase", placeholder="Ex: Je joue depuis 2 ans...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        surveillance_channel = discord.utils.get(guild.text_channels, name="surveillance-hygiene")
        
        embed = discord.Embed(title="🕵️ Nouveau Dossier en Surveillance d'Hygiène", color=discord.Color.purple())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Candidat", value=interaction.user.mention, inline=False)
        embed.add_field(name="Pseudo Zooba", value=self.zooba_id.value, inline=True)
        embed.add_field(name="Trophées", value=self.trophees.value, inline=True)
        embed.add_field(name="Présentation", value=self.presentation.value, inline=False)

        view = RecrutementActionView(interaction.user.id)
        if surveillance_channel:
            await surveillance_channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Votre candidature a bien été transmise au chef dans la réserve !", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erreur : Le salon `#surveillance-hygiene` est introuvable par le bot.", ephemeral=True)

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
            try:
                await member.send("🎉 Félicitations ! Votre candidature pour le clan **LA QUENTINE** a été acceptée en cuisine !\n\nBienvenue chef ! 👨‍🍳")
            except:
                pass
        else:
            await interaction.response.send_message("❌ Membre introuvable sur le serveur.", ephemeral=True)

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
    await interaction.response.send_message("✅ Panneau de recrutement déployé !", ephemeral=True)


# --- 8. COMMANDES ADMIN UTILES ---
@bot.tree.command(name="quentine_give_pourboires", description="[Admin] Donnez des pourboires à un membre.")
async def quentine_give_pourboires(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return
    
    u_data = get_user_data(membre.id)
    u_data["pourboires"] += montant
    update_user_data(membre.id, "pourboires", u_data["pourboires"])
    
    embed = discord.Embed(
        title="💰 Distribution de Pourboires",
        description=f"{membre.mention} a reçu **{montant} Pourboires 🪙**\n\nSolde : {u_data['pourboires']} 🪙",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_reset_user", description="[Admin] Réinitialiser les données d'un utilisateur.")
async def quentine_reset_user(interaction: discord.Interaction, membre: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return
    
    data = load_data()
    uid = str(membre.id)
    data[uid] = {
        "pourboires": 100,
        "main_zooba": "Non défini",
        "brigade": "Aucune",
        "victoires_duels": 0,
        "etoiles_michelin": [],
        "trophees_debut_saison": 0,
        "trophees_actuels": 0,
        "niveau_cuisine": 1,
        "experience": 0,
        "specialite": "Aucune",
        "badges": [],
        "historique_duels": [],
        "total_gains": 0
    }
    save_data(data)
    
    await interaction.response.send_message(f"✅ Données de {membre.mention} réinitialisées !", ephemeral=True)

@bot.tree.command(name="quentine_stats_globales", description="[Admin] Affiche les stats globales du clan.")
async def quentine_stats_globales(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Réservé au patron du restaurant !", ephemeral=True)
        return
    
    data = load_data()
    
    total_membres = len(data)
    total_pourboires = sum(u["pourboires"] for u in data.values())
    total_gains = sum(u.get("total_gains", 0) for u in data.values())
    total_duels = sum(u["victoires_duels"] for u in data.values())
    
    embed = discord.Embed(title="📊 Statistiques Globales - LA QUENTINE", color=discord.Color.blue())
    embed.add_field(name="👥 Membres Actifs", value=str(total_membres), inline=True)
    embed.add_field(name="🪙 Pourboires en Circulation", value=f"{total_pourboires} 🪙", inline=True)
    embed.add_field(name="💰 Gains Totaux Générés", value=f"{total_gains} 🪙", inline=True)
    embed.add_field(name="⚔️ Duels Joués", value=str(total_duels), inline=True)
    
    await interaction.response.send_message(embed=embed)


# --- 9. AIDE & DOCUMENTATION ---
@bot.tree.command(name="quentine_aide", description="Affiche toutes les commandes disponibles.")
async def quentine_aide(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Guide Complet - LA QUENTINE", color=discord.Color.orange())
    
    embed.add_field(
        name="👤 Profil & Personnalisation",
        value="`/quentine_choix_brigade` - Choisir votre brigade\n`/quentine_choix_specialite` - Choisir votre animal Zooba\n`/quentine_carte` - Voir votre profil",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Combats & Compétition",
        value="`/quentine_duel` - Défier un autre membre\n`/quentine_historique_duels` - Voir vos duels\n`/quentine_saison_classement` - Voir le classement",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Saisons (Admin)",
        value="`/quentine_saison_ouvrir` - Ouvrir une nouvelle saison\n`/quentine_saison_cloture` - Clôturer la saison",
        inline=False
    )
    
    embed.add_field(
        name="🛍️ Boutique",
        value="`/quentine_shop` - Voir la boutique\n`/quentine_acheter` - Acheter un item",
        inline=False
    )
    
    embed.add_field(
        name="🚪 Recrutement",
        value="`/quentine_menu_recrutement` - Afficher le panneau de recrutement (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📊 Admin",
        value="`/quentine_stats_globales` - Voir les stats du clan\n`/quentine_give_pourboires` - Donner des pourboires\n`/quentine_reset_user` - Réinitialiser un membre",
        inline=False
    )
    
    embed.add_field(
        name="🌐 Bonus",
        value="Réagissez avec 🌐 à un message non-français pour obtenir la traduction !",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ⚠️ N'oublie pas d'ajouter la bibliothèque googletrans dans ton fichier requirements.txt
# Lancement du bot
bot.run("mets_ton_token_discord_ici")
